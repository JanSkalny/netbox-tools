#!/usr/bin/env python3

import argparse
import os
from sys import exit, stderr

import pynetbox

from netbox_filter_common import add_filter_argument, filter_endpoint


def fail(*messages):
  print(*messages, file=stderr)
  exit(1)


def main():
  parser = argparse.ArgumentParser(description='List NetBox prefixes.')
  parser.add_argument('-t', '--tenant', help='Filter by tenant slug')
  parser.add_argument('-g', '--tag', help='Filter by tag slug')
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

  if args.tag:
    tag = nb.extras.tags.get(slug=args.tag)
    if not tag:
      fail('no such tag:', args.tag)
    filters['tag'] = tag.slug

  prefixes = filter_endpoint(
    nb,
    parser,
    nb.ipam.prefixes,
    args.filter,
    base_filters=filters,
  )

  for prefix in prefixes:
    print(prefix.prefix)


if __name__ == '__main__':
  main()
