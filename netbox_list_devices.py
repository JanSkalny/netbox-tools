#!/usr/bin/env python3

import argparse
import os

import pynetbox

from netbox_filter_common import add_filter_argument, filter_endpoint, has_exact_filter


def main():
  parser = argparse.ArgumentParser(description='List NetBox device names, one per line.')
  parser.add_argument('-T', '--token', help='NetBox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='NetBox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  parser.add_argument('-t', '--tenant', help='Filter by tenant slug or ID')
  parser.add_argument('--site', help='Filter by site slug or ID')
  parser.add_argument('-r', '--role', help='Filter by device role slug or ID')
  parser.add_argument('-s', '--status', default='active', help='Filter by status (defaults to active)')
  add_filter_argument(parser)
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, token=args.token)
  filters = {}
  if not has_exact_filter(args.filter, 'status'):
    filters['status'] = args.status
  for key in ('tenant', 'site', 'role'):
    value = getattr(args, key)
    if value:
      filters[f'{key}_id' if value.isdecimal() else key] = value

  devices = filter_endpoint(
    nb,
    parser,
    nb.dcim.devices,
    args.filter,
    base_filters=filters,
  )
  for device in devices:
    print(device.name)


if __name__ == '__main__':
  main()
