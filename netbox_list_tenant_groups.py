#!/usr/bin/env python3

import argparse
import os

import pynetbox

from netbox_filter_common import add_filter_argument, filter_endpoint


def main():
  parser = argparse.ArgumentParser(description='List NetBox tenant groups.')
  parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  parser.add_argument('--names', action='store_true', help='Display tenant group names instead of slugs')
  add_filter_argument(parser)
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, args.token)

  tenant_groups = filter_endpoint(
    nb,
    parser,
    nb.tenancy.tenant_groups,
    args.filter,
  )
  for tenant_group in tenant_groups:
    print(tenant_group.name if args.names else tenant_group.slug)


if __name__ == '__main__':
  main()
