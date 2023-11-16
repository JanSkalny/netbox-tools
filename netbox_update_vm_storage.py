#!/usr/bin/env python3

from sys import stderr,exit,argv
import json,yaml,os,ipaddress,random,pynetbox,argparse
import requests as req
from pprint import pprint
from uuid import uuid4

# display error & bail out
def fail(*messages):
  print(*messages, file=stderr)
  exit(1)


if __name__ == "__main__":
  # parse inputs
  parser = argparse.ArgumentParser()
  parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  parser.add_argument('-t', '--tenant', help='Tenant name (defaults to NETBOX_DEFAULT_TENANT env)', default=os.getenv('NETBOX_DEFAULT_TENANT'))
  parser.add_argument('-v', '--vm', help='VM name', required=True)
  parser.add_argument('-i', '--id', help='SAN LUN or DRBD Resource ID (custom field "storage_id")', type=int)
  parser.add_argument('-p', '--pool', help='Storage pool (ie. "mixed", "fast", "slow". defaults to None')
  parser.add_argument('-y', '--type', help='Storage type (ie. "drbd", "lvm" or "multipath")', required=True)
  parser.add_argument('-d', '--device', help='Name of storage device (eg. "sto-1") or "None". Required for storage type "multipath".')
  parser.add_argument('-X', '--tmp-lun', help='TMP dynamic lun', type=int)
  parser.add_argument('-Y', '--tmp-name', help='TMP old name')
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, args.token)

  # pre-validate inputs
  if args.type not in ['multipath','drbd','lvm']:
    fail("Invalid storage type")
  if args.pool and args.pool not in ['slow','mixed','fast','vg0','vg1']:
    fail("Invalid storage pool")
  if args.id and (args.id < 1 or args.id > 255):
    fail("invalid storage id")

  # lookup storage device, if specified
  storage_dev = None
  if args.device and args.device != 'None':
    storage_dev = nb.dcim.devices.get(name=args.device)
    if not storage_dev:
      fail("no such storage device")
    if storage_dev.device_role.name not in ['Storage', 'Cluster Node']:
      fail("non-storage storage device specified")

  # make sure VM does not already exist
  vm = nb.virtualization.virtual_machines.get(name=args.vm)
  if not vm:
    fail("VM not found")

  if storage_dev:
    vm.custom_fields['storage_device'] = storage_dev.id
  if args.device == 'None':
    vm.custom_fields['storage_device'] = None

  if args.id:
    vm.custom_fields['storage_id'] = args.id
  if args.pool:
    vm.custom_fields['storage_pool'] = args.pool

  if args.tmp_lun:
    vm.custom_fields['tmp_storage_dynamic_lun'] = args.tmp_lun
  if args.tmp_name:
    vm.custom_fields['tmp_storage_old_name'] = args.tmp_name


  vm.custom_fields['storage_type'] = args.type

  vm.save()

