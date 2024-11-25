#!/usr/bin/env python3

from sys import stderr,exit,argv
import os,ipaddress,random,pynetbox,argparse,ast,re
from pprint import pprint
from uuid import uuid4

# display error & bail out
def fail(*messages):
  print(*messages, file=stderr)
  exit(1)

# display warning message
def warn(*messages):
  print(*messages, file=stderr)

# display debug message
def debug(*messages):
  print(*messages, file=stderr)

# rollback everything from ROLLBACK_LIST and fail with error
def rollback(*messages):
  if len(ROLLBACK_LIST) > 0:
    warn("rolling back",len(ROLLBACK_LIST),"objects")
  for x in ROLLBACK_LIST:
    try:
      x.delete()
    except Exception as e:
      warn("!! failed to rollback", x)

  print(*messages, file=stderr)
  exit(1)


def assume_ip_gateway(network):
  return str(ipaddress.ip_network(network)[1]).split('/')[0]

def generate_mac():
  prefix = [0x52, 0x54, 0x00]
  suffix = [random.randint(0,0xFF) for _ in range(3)]
  return ':'.join(map(lambda x: "%02x" % x, [*prefix, *suffix] ))

def assign_lun_for_cluster(nb, cluster):
  assigned_luns = []
  vms = nb.virtualization.virtual_machines.filter(cluster=cluster)
  for vm in vms:
    assigned_luns.append(vm.custom_fields['storage_id'])
  for lun in range(1, 500):
    if lun not in assigned_luns:
      return lun

  fail('failed to assign lun')
  return None

def test_lun_uniqness(nb, cluster, lun, assigned_vm_id):
  vms = nb.virtualization.virtual_machines.filter(cluster=cluster)
  for vm in vms:
    if vm.custom_fields['storage_id'] == lun and vm.id != assigned_vm_id:
      warn('lun was assigned to different vm object...', vm)
      return False
    if vm.id == assigned_vm_id and vm.custom_fields['storage_id'] != lun:
      warn('vm got assigned different lun...')
      return False
  return True

def test_uuid_uniqness(nb, uuid, short=False):
  # build list of all uuids in short and long form
  uuids = []
  short_uuids = []
  for vm in nb.virtualization.virtual_machines.all():
    if not vm.custom_fields['uuid']:
      warn('vm without uuid', vm.name)
      continue
    uuids.append(vm.custom_fields['uuid'])
    short_uuids.append(vm.custom_fields['uuid'].split('-')[0])

  # test uniqeness
  if uuid in uuids:
    return False
  if short:
    if uuid.split('-')[0] in short_uuids:
      return False
  return True

parser = argparse.ArgumentParser()
parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
parser.add_argument('-t', '--tenant', help='Tenant name (defaults to NETBOX_DEFAULT_TENANT env)', default=os.getenv('NETBOX_DEFAULT_TENANT'))
parser.add_argument('-c', '--cluster', help='Cluster name (defaults to NETBOX_DEFAULT_CLUSTER env)', default=os.getenv('NETBOX_DEFAULT_CLUSTER'))
parser.add_argument('-s', '--site', help='Site name (defaults to NETBOX_DEFAULT_SITE env)', default=os.getenv('NETBOX_DEFAULT_SITE'))
parser.add_argument('--short-uuids', help='Use short UUIDs (defaults to NETBOX_SHORT_UUIDS env or False)', default=ast.literal_eval(os.getenv('NETBOX_SHORT_UUIDS', 'False')), action='store_true')
parser.add_argument('-n', '--name', help='VM name, eg. "vm-ipam.example.com".', required=True)
parser.add_argument('-f', '--fqdn', help='FQDN associated with VMs primary IP. Defaults to VM name, if FQDN is used.')
parser.add_argument('-r', '--ram-size', help='RAM in MBs', required=True, type=int)
parser.add_argument('-C', '--cpus', help='Number of cpu cores (default 2)', default=2, type=int)
parser.add_argument('-d', '--disk-size', help='Disk size in GBs', required=True, type=int)
parser.add_argument('-S', '--storage-type', help='[cf] Storage type. How will hypervisor access storage device. (defaults to multipath)', default='multipath', choices=['multipath', 'lvm', 'drbd'],)
parser.add_argument('-D', '--storage-device', help='[cf] Storage device name. Must exist as device with "storage" or "cluster_node" roles under same site. Assign both devices for DRBD. (eg. "sto-1" or "srv-xxx-1")', nargs="+", required=True)
parser.add_argument('-P', '--storage-pool', help='[cf] Storage pool. Either vg name, or storage class. (eg. "vg0", "mixed", "fast", "slow", ...)', default='mixed')
parser.add_argument('-L', '--storage-fixed-lun', help='[cf] Fixed LUN/DRBD Res ID assignment. Avoid using this. LUN will be automatically assigned by this script.', type=int)
parser.add_argument('-v', '--vlan-id', help='Vlan for primary IP address (within site)', required=True, type=int)
parser.add_argument('-p', '--platform', help='Platform slug (defaults to "ubuntu22")', default='ubuntu22')
parser.add_argument('-B', '--batch', help='Run in batch mode. Don\'t ask for confirmations or rollbacks', default=False, action='store_true')
parser.add_argument('-m', '--mac-addr', help='Manually select primary interface MAC address. By defaults generates MAC from 52:54:00 OUI')
parser.add_argument('-i', '--ip-addr', help='Manually select IP address. By default assigns first usable and free IP from block associated with VLAN')
parser.add_argument('-u', '--uuid', help='Manually select UUID for VM. By default automatically generates one')

args = parser.parse_args()

# connect to netbox
nb = pynetbox.api(args.api_url, args.token)

ROLLBACK_LIST = []

print("pre-flight checks...")

# pre-validate inputs
if args.ram_size <= 50:
  fail("Too little ram?")
if args.disk_size <= 1:
  fail("Too little disk space?")
if not args.vlan_id in range (2, 4094 +1):
  fail("VLAN-ID should be between 2 and 4094")
if not args.cpus in range(1, 40):
  fail("How many CPU cores??")
if args.tenant == None:
  fail("invalid tenant")
if args.site == None:
  fail("invalid site")
if args.cluster == None:
  fail("invalid cluster")

if args.storage_type == 'drbd':
  if len(args.storage_device) != 2:
    fail('drbd storage type requires exactly two storage devices specified')
else:
  if len(args.storage_device) != 1:
    fail('exactly one storage device is required')

# lookup storage devices
storage_devices = []
for storage_name in args.storage_device:
  storage_dev = nb.dcim.devices.get(name=storage_name)
  if not storage_dev:
    fail("no such storage device", storage_name)
  if storage_dev.device_role.name not in ['Storage', 'Cluster Node', 'Hypervisor']:
    fail("non-storage storage device specified", storage_name)
  #TODO: validate site!
  storage_devices.append(storage_dev)

if args.storage_type == 'multipath':
  if len(storage_devices) != 1:
    fail('invalid amount of storage devices found')
if args.storage_type == 'drbd':
  if len(storage_devices) != 2:
    fail('invalid amount of storage devices found')

if args.uuid:
  # make sure uuid from user is unique
  if not test_uuid_uniqness(nb, args.uuid, args.short_uuids):
    fail("uuid specified is not unique")
  vm_uuid = args.uuid
else:
  # generate vm uuid
  for _ in range(0, 10):
    vm_uuid = str(uuid4())
    if test_uuid_uniqness(nb, vm_uuid, args.short_uuids):
      break
  else:
    fail("faield to generate unique uuid")

debug("- uuid", vm_uuid)

# validate storage pools against each storage/server
# and build list of storage_devices_ids
storage_devices_ids = []
for storage_device in storage_devices:
  if not storage_device.custom_fields['storage_valid_pools']:
    fail("no storage pools defined for storage", storage_device)
  if not args.storage_pool in storage_device.custom_fields['storage_valid_pools']:
    fail("storage pool", args.storage_pool, "is not valid for", storage_device, "valid are", storage_device.custom_fields['storage_valid_pools'])
  storage_devices_ids.append(storage_device.id)
debug("-", args.disk_size,"GBs on storage pool", args.storage_pool, "storage(s)", storage_devices)

# decide on name and fqdn
fqdn = None
if '.' not in args.name:
  if not args.fqdn:
    fail('name must be fqdn or --fqdn must be specified as well')
  if '.' not in args.fqdn:
    fail('invalid fqdn specified')
  else:
    fqdn = args.fqdn
else:
  fqdn = args.name

# make sure VM does not already exist
vm = nb.virtualization.virtual_machines.get(name=args.name)
if vm:
  fail("VM with speicified name already exists")

# find the tenant object
tenant = nb.tenancy.tenants.get(slug=args.tenant)
if not tenant:
  fail("no such tenant")

# fint the site object
site = nb.dcim.sites.get(slug=args.site)
if not site:
  fail("no such site")

# find the platform object
platform = nb.dcim.platforms.get(slug=args.platform)
if not platform:
  fail("no such platform")
debug("- platform", platform)

# find the cluster object
cluster = nb.virtualization.clusters.get(name=args.cluster)
if not cluster:
  fail("no such cluster")

# find network prefix with specified vlan
net = nb.ipam.prefixes.get(vlan_vid=args.vlan_id)
if not net:
  fail("no such vlan")
debug("- network", net.description)

if args.mac_addr:
  # test user supplied mac address
  mac = args.mac_addr
  iface = nb.virtualization.interfaces.get(mac_address=mac)
  if iface:
    fail("interface with same mac address already exists")
  if not re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', mac):
    fail("invalid mac address specified")
else:
  # generate and verify uniqueness of mac address
  for _ in range(10):
    mac = generate_mac()
    iface = nb.virtualization.interfaces.get(mac_address=mac)
    if not iface:
      break
  else:
    fail("couldnt generate unique mac after 10 tries")

ip_data = {
  "dns_name": fqdn,
  "tenant": tenant.id,
  "family": 4
}

if args.ip_addr:
  # check if ip address belongs to same network as vlan and if it's free
  available_ips = net.available_ips.list()
  if not any(ip.address == args.ip_addr for ip in available_ips):
    rollback("selected IP address is not valid. valid addresses are ", available_ips)
  ip_data['address'] = args.ip_addr
  # create requested ip 
  ip = nb.ipam.ip_addresses.create(ip_data)
else: 
  # get usable ip address in the prefix and allocate it
  ip = net.available_ips.create(ip_data)

if not ip:
  rollback("failed to allocate address")
if args.ip_addr:
  debug("- assigned requested address", ip)
else:
  debug("- assigned address", ip)
ROLLBACK_LIST.insert(0, ip)

# make sure allocated address is not gateway address
gateway_ip = assume_ip_gateway(net.prefix)
if ip.address.split('/')[0] == gateway_ip:
  rollback("allocated gateway address! fix your netbox")

# allocate unique storage_id, if not fixed lun specified
lun = None
if args.storage_fixed_lun:
  lun = args.storage_fixed_lun
else:
  lun = assign_lun_for_cluster(nb, args.cluster)

# create new vm
vm_data = {
  "name": args.name,
  "status": 'planned',
  "cluster": cluster.id,
  "role": {'slug': 'server'},
  "site": site.id,
  "tenant": tenant.id,
  "platform": platform.id,
  "vcpus": args.cpus,
  "memory": args.ram_size,
  "disk": args.disk_size,
  "custom_fields": {
    "uuid": vm_uuid,
    "storage_device": storage_devices_ids,
    "storage_pool": args.storage_pool,
    "storage_type": args.storage_type,
    "storage_id": lun,
  }
}
try:
  vm = nb.virtualization.virtual_machines.create(vm_data)
except Exception as e:
  vm = None
  warn(e)
if not vm:
  rollback("failed to create VM")
ROLLBACK_LIST.append(vm)

# make sure lun is still unique...
#TODO: better race condition handling?
if not test_lun_uniqness(nb, args.cluster, lun, vm.id):
  rollback("potential lun conflict detected. re-run netbox_create_vm.py")

# create "eth0" interface
iface_data = {
  "virtual_machine": vm.id,
  "name": "eth0",
  "type": 'virtual',
  "mac_address": mac,
  "mode": "access",
  "untagged_vlan": net.vlan.id
}
try:
  iface = nb.virtualization.interfaces.create(iface_data)
except Exception as e:
  iface = None
  warn(e)
if not iface:
  rollback("failed to create interface")
ROLLBACK_LIST.insert(1,iface)
debug("- mac", mac)

# associate interface with vm
ip.assigned_object_id = iface.id
ip.assigned_object_type = "virtualization.vminterface"
res = ip.save()
if res == False:
  rollback("failed to assign address to interface")

# if upgrade_interval is present, set it to 30 days
if 'upgrade_interval' in vm.custom_fields:
  vm.custom_fields['upgrade_interval'] = 30

# make ip address primary of our vm
vm.primary_ip4 = ip.id
res = vm.save()
if res == False:
  rollback("failed to declare ip address as primary")

debug("")
debug(f"succesfuly created new vm {vm.name}")
debug("")

# no questions in batch mode
if args.batch:
  exit(0)

# ask user if he wants to rollback everything :D
while True:
  confirm = input("> last chance to rollback. rollback? [y/n] ")
  if confirm in ('y', 'n'):
    break

if confirm == 'y':
  rollback('user requested rollback')

