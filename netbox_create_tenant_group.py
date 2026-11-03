#!/usr/bin/env python3

import argparse
import os
from sys import exit, stderr

import pynetbox


def fail(*messages):
  print(*messages, file=stderr)
  exit(1)


def main():
  parser = argparse.ArgumentParser(description='Create a NetBox tenant group.')
  parser.add_argument('name', help='Tenant group name')
  parser.add_argument('-s', '--slug', help='Tenant group slug (defaults to the lowercase name with spaces replaced by dashes)')
  parser.add_argument('-T', '--token', help='NetBox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='NetBox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  slug = args.slug if args.slug is not None else args.name.lower().replace(' ', '-')
  nb = pynetbox.api(args.api_url, token=args.token)

  if nb.tenancy.tenant_groups.get(slug=slug):
    fail('tenant group with slug already exists:', slug)

  tenant_group = nb.tenancy.tenant_groups.create({
    'name': args.name,
    'slug': slug,
  })
  print(tenant_group.slug)


if __name__ == '__main__':
  main()
