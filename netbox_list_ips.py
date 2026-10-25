#!/usr/bin/env python3

import argparse
import json
import os
from sys import exit, stderr

import pynetbox

from netbox_filter_common import add_filter_argument, filter_endpoint


OUTPUT_FIELDS = ('address', 'id', 'json')


def fail(*messages):
  print(*messages, file=stderr)
  exit(1)


def output_ip(ip, output):
  if output == 'json':
    print(json.dumps(ip.serialize(), sort_keys=True))
  else:
    value = getattr(ip, output, None)
    print('' if value is None else value)


def main():
  parser = argparse.ArgumentParser(description='List NetBox IP addresses.')
  parser.add_argument('-o', '--output', choices=OUTPUT_FIELDS, default='address',
                      help='Value to display for each IP address (default: address)')
  parser.add_argument('-t', '--tenant', help='Filter by tenant slug')
  parser.add_argument('-T', '--token', help='NetBox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='NetBox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  add_filter_argument(parser)
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, token=args.token)
  filters = {}
  if args.tenant:
    tenant = nb.tenancy.tenants.get(slug=args.tenant)
    if not tenant:
      fail('no such tenant:', args.tenant)
    filters['tenant_id'] = tenant.id

  ips = filter_endpoint(
    nb,
    parser,
    nb.ipam.ip_addresses,
    args.filter,
    base_filters=filters,
  )

  for ip in ips:
    output_ip(ip, args.output)


if __name__ == '__main__':
  main()
