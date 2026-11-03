#!/usr/bin/env python3

import argparse
import os
from sys import exit, stderr

import pynetbox


TENANT_OBJECT_TYPE = 'tenancy.tenant'


def fail(*messages):
  print(*messages, file=stderr)
  exit(1)


def main():
  parser = argparse.ArgumentParser(
    description='List tenant slugs assigned to a NetBox contact.'
  )
  parser.add_argument('contact_id', type=int, help='Contact ID')
  parser.add_argument('-T', '--token', help='NetBox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='NetBox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, token=args.token)
  if not nb.tenancy.contacts.get(id=args.contact_id):
    fail('no such contact:', args.contact_id)

  tenant_slugs = set()
  assignments = nb.tenancy.contact_assignments.filter(
    contact_id=args.contact_id,
    object_type=TENANT_OBJECT_TYPE,
  )
  for assignment in assignments:
    tenant = nb.tenancy.tenants.get(id=assignment.object_id)
    if tenant:
      tenant_slugs.add(tenant.slug)

  for slug in sorted(tenant_slugs):
    print(slug)


if __name__ == '__main__':
  main()
