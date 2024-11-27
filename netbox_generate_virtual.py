#!/usr/bin/env python3

from sys import stderr
import json, os, yaml, pynetbox, re, ipaddress, argparse, ast

def warn(*msg):
  print(*msg, file=stderr)

def fail(*msg):
  print(*msg, file=stderr)
  exit(1)

# parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
parser.add_argument('--short-uuids', help='Use short UUIDs (defaults to NETBOX_SHORT_UUIDS env or False)', default=ast.literal_eval(os.getenv('NETBOX_SHORT_UUIDS', 'False')), action='store_true')
parser.add_argument('-u', '--uuid', help='Use "vm-UUID" as technical name for VM, instead of name (defaults to false)', action='store_true')
parser.add_argument('-f', '--fqdn', help='Make extra sure that vm.fqdn is FQDN. (defaults to false)', action='store_true')
parser.add_argument("-n", '--name', help='VM name', required=True)
args = parser.parse_args()

# connect to netbox
nb = pynetbox.api(args.api_url, args.token)

# find vm object
vm = nb.virtualization.virtual_machines.get(name=args.name)
if vm is None:
  fail("no such vm")

# find primary ip object
ip = nb.ipam.ip_addresses.get(vm.primary_ip.id)
if ip is None:
  fail("invalid primary ip")

# decide which tech_name to use
if args.uuid:
  if args.short_uuids:
    tech_name = f'vm-{vm.custom_fields["uuid"].split("-")[0]}'
  else:
    tech_name = f'vm-{vm.custom_fields["uuid"]}'
else:
  tech_name = args.name
  
# decide storage device based on storage_type, pool and tech_name
disk_blk = None
st = vm.custom_fields['storage_type']
if st == 'lvm':
  disk_blk = f'/dev/{vm.custom_fields["storage_pool"]}/{tech_name}'
elif st == 'drbd':
  disk_blk = f'/dev/drbd/by-res/{tech_name}/0'
elif st == 'multipath':
  disk_blk = f'/dev/mapper/{tech_name}'

# choose cluster node for preseeding
cluster_nodes = nb.dcim.devices.filter(cluster_id=vm['cluster']['id'])
if len(cluster_nodes) == 0:
  fail("cluster without nodes!")
chosen_node = list(cluster_nodes)[0]

# make sure to use fqdn of choosen node
preseed_host_fqdn = None
if '.' in chosen_node.name:
  preseed_host_fqdn = chosen_node.name
elif 'fqdn' in chosen_node.custom_fields and chosen_node.custom_fields['fqdn'] and '.' in chosen_node.custom_fields['fqdn']:
  preseed_host_fqdn = chosen_node.custom_fields['fqdn']
else:
  chosen_node.primary_ip.full_details()
  if '.' in chosen_node.primary_ip4.dns_name:
    preseed_host_fqdn = chosen_node.primary_ip4.dns_name
if not preseed_host_fqdn:
  fail('failed to find fqdn for preseed host')

# make sure fqdn is fqdn, if requested.. otherwise just use vm.name
if args.fqdn:
  fqdn = None
  if '.' in vm.name:
    fqdn = vm.name
  elif 'fqdn' in vm.custom_fields and '.' in vm.custom_fields['fqdn']:
    fqdn = vm.custom_fields['fqdn']
  else:
    if '.' in ip.dns_name:
      fqdn = ip.dns_name
  if not fqdn:
    fail('failed to find fqdn for vm')
else:
  fqdn = vm.name

# make sure vm is in planned, staging or active phase
if str(vm.status) not in ['Planned','Staged','Active']:
  fail(vm.name, 'is in invalid state', vm.status)

# construct "virtual" configuration
res = {
        'name': tech_name,
        'fqdn': fqdn,
        'uuid': vm.custom_fields['uuid'],
        'cpus': int(vm['vcpus']),
        'ram': int(vm['memory']),
        'disk_size': int(vm['disk']),
        'disk_blk': disk_blk,
        'cluster': vm['cluster']['name'].replace('-','_'),
        'host': preseed_host_fqdn,
    }

if vm.custom_fields.get('service_group', None):
  res['service_group'] = vm.custom_fields['service_group']

print("# generated from netbox. do not change manually")
print(yaml.dump({'virtual':res}))
