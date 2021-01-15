#!/usr/bin/env python3

from sys import stderr,exit,argv
import os,ipaddress,random,pynetbox,argparse
from pprint import pprint
from uuid import uuid4

# display error & bail out
def fail(*messages):
  print(*messages, file=stderr)
  exit(1)

def assume_ip_gateway(network):
  return str(ipaddress.ip_network(network)[1]).split('/')[0]

# generate uuid
uuid = lambda: str(uuid4())

def generate_mac():
  prefix = [0x52, 0x54, 0x00] 
  suffix = [random.randint(0,0xFF) for _ in range(3)]
  return ':'.join(map(lambda x: "%02x" % x, [*prefix, *suffix] ))

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  parser.add_argument('-t', '--tenant', help='Tenant name (defaults to NETBOX_DEFAULT_TENANT env)', default=os.getenv('NETBOX_DEFAULT_TENANT'))
  parser.add_argument('-c', '--cluster', help='Cluster name (defaults to NETBOX_DEFAULT_CLUSTER env)', default=os.getenv('NETBOX_DEFAULT_CLUSTER'))
  parser.add_argument('-s', '--site', help='Site name (defaults to NETBOX_DEFAULT_SITE evn)', default=os.getenv('NETBOX_DEFAULT_SITE'))
  parser.add_argument('-n', '--name', help='VM name, eg. "vm-netbox-2"', required=True, )
  parser.add_argument('-f', '--fqdn', help='FQDN associated with VMs primary IP', required=True)
  parser.add_argument('-r', '--ram-size', help='RAM in MBs', required=True, type=int)
  parser.add_argument('-C', '--cpus', help='Number of cpu cores (default 2)', default=2, type=int)
  parser.add_argument('-d', '--disk-size', help='Disk size in GBs', required=True, type=int)
  parser.add_argument('-S', '--storage', help='Storage profile (custom field "storage")', default='slow')
  parser.add_argument('-v', '--vlan-id', help='Vlan for primary IP address (within site)', required=True, type=int)
  parser.add_argument('-p', '--platform', help='Platform slug (defaults to "ubuntu18")', default='ubuntu18')

  args = parser.parse_args()

  # connect to netbox
  nb = pynetbox.api(args.api_url, args.token)
  
  # pre-validate inputs
  if args.ram_size <= 50:
    fail("Too little ram?")
  if args.disk_size <= 1:
    fail("Too little disk space?")
  if not args.vlan_id in range (2, 4094 +1): 
    fail("VLAN-ID should be between 2 and 4094")
  if not args.cpus in range(1, 40):
    fail("How many CPU cores??")
  if args.storage not in ['slow','fast','drbd','lv']:
    fail("Invalid storage profile")
  if args.tenant == None:
    fail("invalid tenant")
  if args.site == None:
    fail("invalid site")
  if args.cluster == None:
    fail("invalid cluster")

  # make sure VM does not already exist
  vm = nb.virtualization.virtual_machines.get(name=args.name)
  if vm:
    fail("VM with speicified name already exists")

  # find the tenant object
  tenant = nb.tenancy.tenants.get(name=args.tenant)
  if not tenant:
    fail("no such tenant")

  # fint the site object
  site = nb.dcim.sites.get(name=args.site)
  if not site:
    fail("no such site")
  
  # find the platform object
  platform = nb.dcim.platforms.get(slug=args.platform)
  if not platform:
    fail("no such platform")

  # find the cluster object
  cluster = nb.virtualization.clusters.get(name=args.cluster)
  if not cluster:
    fail("no such cluster")
  
  # find network prefix with specified vlan
  net = nb.ipam.prefixes.get(vlan_vid=args.vlan_id)
  if not net:
    fail("no such vlan")

  # generate and verify uniqueness of mac address 
  for _ in range(10):
    mac = generate_mac()
    iface = nb.virtualization.interfaces.get(mac_address=mac)
    if not iface:
      break
  else:
    fail("couldnt generate unique mac after 10 tries")

  # get first usable ip address in the prefix and allocate it 
  ip_data = {
    "dns_name": args.fqdn,
    "tenant": tenant.id,
    "family": 4
  }
  ip = net.available_ips.create(ip_data)
  if not ip:
    fail("failed to allocate address")

  # make sure allocated address is not gateway address
  gateway_ip = assume_ip_gateway(net.prefix)
  if ip.address.split('/')[0] == gateway_ip:
    ip.delete()
    fail("allocated gateway address! fix your netbox")

  # create new vm
  vm_data = {
    "name": args.name,
    "status": 'planned',
    "cluster": cluster.id,
    "role": 8,
    "tenant": tenant.id,
    "platform": platform.id,
    "vcpus": args.cpus,
    "memory": args.ram_size,
    "disk": args.disk_size,
    "custom_fields": {
      "uuid": uuid(),
      "storage": args.storage,
    }
  }
  vm = nb.virtualization.virtual_machines.create(vm_data)
  if not vm:
    ip.detele()
    fail("failed to create VM")
  
  # create "eth0" interface
  iface_data = {
    "virtual_machine": vm.id,
    "name": "eth0",
    "type": 'virtual',
    "mac_address": mac,
    "mode": "access",
    "untagged_vlan": net.vlan.id
  }
  iface = nb.virtualization.interfaces.create(iface_data)
  if not iface:
    ip.delete()
    vm.delete()
    fail("failed to create interface")
 
  # associate interface with vm
  ip.assigned_object_id = iface.id
  ip.assigned_object_type = "virtualization.vminterface"
  res = ip.save()
  if res == False:
    ip.delete()
    vm.delete()
    fail("failed to assign address to interface")

  # make ip address primary of our vm
  vm.primary_ip4 = ip.id
  res = vm.save()
  if res == False:
    ip.delete()
    vm.delete()
    fail("failed to declare ip address as primary")

  # create service 'tcp/22' with same name as fqdn
  service_data = {
          'name': args.fqdn,
          'protocol': 'tcp',
          'ports': [22],
          'virtual_machine': vm.id,
  }
  service = nb.ipam.services.create(service_data)
  if not service:
    ip.delete()
    vm.delete()
    fail("failed to create service")

if __name__ == "__main__":
  main()
