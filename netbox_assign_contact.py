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
    description='Assign a NetBox contact to a tenant unless that assignment already exists.'
  )
  parser.add_argument('contact_id', type=int, help='Contact ID')
  parser.add_argument('tenant', help='Tenant slug')
  parser.add_argument('role', nargs='?', help='Optional contact role slug')
  parser.add_argument('-T', '--token', help='NetBox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='NetBox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, token=args.token)

  contact = nb.tenancy.contacts.get(id=args.contact_id)
  if not contact:
    fail('no such contact:', args.contact_id)

  tenant = nb.tenancy.tenants.get(slug=args.tenant)
  if not tenant:
    fail('no such tenant:', args.tenant)

  assignments = nb.tenancy.contact_assignments.filter(
    contact_id=contact.id,
    object_type=TENANT_OBJECT_TYPE,
    object_id=tenant.id,
  )
  for assignment in assignments:
    print(assignment.id)
    return

  assignment_data = {
    'object_type': TENANT_OBJECT_TYPE,
    'object_id': tenant.id,
    'contact': contact.id,
  }
  if args.role is not None:
    role = nb.tenancy.contact_roles.get(slug=args.role)
    if not role:
      fail('no such contact role:', args.role)
    assignment_data['role'] = role.id

  assignment = nb.tenancy.contact_assignments.create(assignment_data)
  print(assignment.id)


if __name__ == '__main__':
  main()
