#!/usr/bin/env python3

import argparse
import os
from sys import exit, stderr

import pynetbox


def fail(*messages):
  print(*messages, file=stderr)
  exit(1)


def main():
  parser = argparse.ArgumentParser(description='Update an existing NetBox tenant.')
  parser.add_argument('slug', help='Slug of the tenant to update')
  parser.add_argument('--new-name', help='New tenant name')
  parser.add_argument('--new-slug', help='New tenant slug')
  parser.add_argument('--new-tenant-group', help='Slug of the new tenant group')
  parser.add_argument('-T', '--token', help='NetBox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='NetBox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  if args.new_name is None and args.new_slug is None and args.new_tenant_group is None:
    parser.error('at least one of --new-name, --new-slug, and --new-tenant-group is required')

  nb = pynetbox.api(args.api_url, token=args.token)
  tenant = nb.tenancy.tenants.get(slug=args.slug)
  if not tenant:
    fail('no such tenant:', args.slug)

  if args.new_slug is not None and args.new_slug != args.slug:
    if nb.tenancy.tenants.get(slug=args.new_slug):
      fail('tenant with slug already exists:', args.new_slug)

  update_data = {}
  if args.new_name is not None:
    update_data['name'] = args.new_name
  if args.new_slug is not None:
    update_data['slug'] = args.new_slug
  if args.new_tenant_group is not None:
    tenant_group = nb.tenancy.tenant_groups.get(slug=args.new_tenant_group)
    if not tenant_group:
      fail('no such tenant group:', args.new_tenant_group)
    update_data['group'] = tenant_group.id

  tenant.update(update_data)
  print(args.new_slug if args.new_slug is not None else args.slug)


if __name__ == '__main__':
  main()
