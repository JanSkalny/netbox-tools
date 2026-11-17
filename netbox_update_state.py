#!/usr/bin/env python3

import argparse
import os
from sys import exit, stderr

import pynetbox


def main():
  parser = argparse.ArgumentParser(description='Update the state of a NetBox VM or device.')
  parser.add_argument('object_type', choices=('vm', 'device'), help='Object type')
  parser.add_argument('identifier', help='Object name or numeric ID')
  parser.add_argument('--status', required=True, help='New NetBox status value')
  parser.add_argument('-n', '--dry-run', action='store_true', help='Show changes without saving')
  parser.add_argument('-T', '--token', default=os.getenv('NETBOX_TOKEN'), help='NetBox API Token (defaults to NETBOX_TOKEN env)')
  parser.add_argument('-A', '--api-url', default=os.getenv('NETBOX_API_URL'), help='NetBox API URL (defaults to NETBOX_API_URL env)')
  args = parser.parse_args()

  try:
    nb = pynetbox.api(args.api_url, token=args.token)
    endpoint = nb.virtualization.virtual_machines if args.object_type == 'vm' else nb.dcim.devices
    lookup = {'id': int(args.identifier)} if args.identifier.isdecimal() else {'name': args.identifier}
    obj = endpoint.get(**lookup)
    if not obj:
      print(f'no such {args.object_type}: {args.identifier}', file=stderr)
      exit(1)

    current = obj.status
    if isinstance(current, dict):
      current = current['value']
    else:
      current = getattr(current, 'value', current)
    if current == args.status:
      return

    if not args.dry_run:
      if not obj.update({'status': args.status}):
        print(f'failed to update state of {args.object_type} {args.identifier}', file=stderr)
        exit(1)
    print(f'status: {current!r} -> {args.status!r}' + (' (dry run)' if args.dry_run else ''))
  except Exception as error:
    print(f'failed to update state of {args.object_type} {args.identifier}: {error}', file=stderr)
    exit(1)


if __name__ == '__main__':
  main()
