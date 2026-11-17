#!/usr/bin/env python3

import argparse
import json
import os
from sys import exit, stderr

import pynetbox


def fail(*messages):
  print(*messages, file=stderr)
  exit(1)


def resolve_id(endpoint, selector, label):
  lookup = {'id': int(selector)} if selector.isdecimal() else {'slug': selector}
  record = endpoint.get(**lookup)
  if not record:
    fail('no such ' + label + ':', selector)
  return record.id


def positive_int(value):
  number = int(value)
  if number <= 0:
    raise argparse.ArgumentTypeError('must be a positive integer')
  return number


def main():
  parser = argparse.ArgumentParser(description='Create a NetBox device.')
  parser.add_argument('-N', '--name', required=True, help='Device name')
  parser.add_argument('--status', default='active', help='NetBox status value (default: active)')
  parser.add_argument('-n', '--dry-run', action='store_true', help='Show planned changes without saving')
  parser.add_argument('-s', '--site', required=True, help='Site slug or ID')
  parser.add_argument('-r', '--role', '--device-role', default='server', help='Device role slug or ID (default: server)')
  parser.add_argument('-D', '--device-type', required=True, help='Device type slug or ID')
  parser.add_argument('-t', '--tenant', help='Tenant slug or ID')
  parser.add_argument('-d', '--description', help='Device description')
  parser.add_argument('--ram-size', '--ram', type=positive_int, help='RAM in MB (device custom field: ram_size)')
  parser.add_argument('--disk-size', '--disk', type=positive_int, help='Disk size in GB (device custom field: disk_size)')
  parser.add_argument('-C', '--cpus', '--cpu', type=positive_int, help='Number of CPU cores (device custom field: cpus)')
  parser.add_argument('-T', '--token', help='NetBox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='NetBox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, token=args.token)
  device_data = {
    'name': args.name,
    'status': args.status,
    'site': resolve_id(nb.dcim.sites, args.site, 'site'),
    'role': resolve_id(nb.dcim.device_roles, args.role, 'device role'),
    'device_type': resolve_id(nb.dcim.device_types, args.device_type, 'device type'),
  }
  if args.tenant is not None:
    device_data['tenant'] = resolve_id(nb.tenancy.tenants, args.tenant, 'tenant')
  if args.description is not None:
    device_data['description'] = args.description
  resources = {field: getattr(args, field) for field in ('ram_size', 'disk_size', 'cpus')
               if getattr(args, field) is not None}
  if resources:
    device_data['custom_fields'] = resources

  if args.dry_run:
    print('Would create device (dry run): ' + json.dumps(device_data, ensure_ascii=False, sort_keys=True))
    return

  device = nb.dcim.devices.create(device_data)
  print(device.id)


if __name__ == '__main__':
  main()
