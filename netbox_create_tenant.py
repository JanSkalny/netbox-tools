#!/usr/bin/env python3

import argparse
import os
from sys import exit, stderr

import pynetbox


def fail(*messages):
  print(*messages, file=stderr)
  exit(1)


def main():
  parser = argparse.ArgumentParser(description='Create a NetBox tenant.')
  parser.add_argument('name', help='Tenant name')
  parser.add_argument('-s', '--slug', help='Tenant slug (defaults to the lowercase name with spaces replaced by dashes)')
  parser.add_argument('-g', '--tenant-group', help='Tenant group slug')
  parser.add_argument('-T', '--token', help='NetBox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='NetBox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  slug = args.slug if args.slug is not None else args.name.lower().replace(' ', '-')
  nb = pynetbox.api(args.api_url, token=args.token)

  if nb.tenancy.tenants.get(slug=slug):
    fail('tenant with slug already exists:', slug)

  tenant_data = {
    'name': args.name,
    'slug': slug,
  }

  if args.tenant_group is not None:
    tenant_group = nb.tenancy.tenant_groups.get(slug=args.tenant_group)
    if not tenant_group:
      fail('no such tenant group:', args.tenant_group)
    tenant_data['group'] = tenant_group.id

  tenant = nb.tenancy.tenants.create(tenant_data)
  print(tenant.slug)


if __name__ == '__main__':
  main()
