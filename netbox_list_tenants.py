#!/usr/bin/env python3

import argparse
import os

import pynetbox

from netbox_filter_common import add_filter_argument, filter_endpoint


def main():
  parser = argparse.ArgumentParser(description='List NetBox tenants.')
  parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  add_filter_argument(parser)
  parser.add_argument('--names', action='store_true', help='Display tenant names instead of slugs')
  parser.add_argument('--with-groups', action='store_true', help='Display tenant slugs followed by tenant group slugs')
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, args.token)

  tenants = filter_endpoint(
    nb,
    parser,
    nb.tenancy.tenants,
    args.filter,
  )
  for tenant in tenants:
    if args.with_groups:
      group = getattr(tenant, 'group', None)
      print(tenant.slug, getattr(group, 'slug', ''))
    else:
      print(tenant.name if args.names else tenant.slug)


if __name__ == '__main__':
  main()
