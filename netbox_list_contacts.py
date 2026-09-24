#!/usr/bin/env python3

import argparse
import json
import os
from sys import exit, stderr

import pynetbox


OUTPUT_FIELDS = ('name', 'phone', 'email', 'id', 'json')
TENANT_OBJECT_TYPE = 'tenancy.tenant'


def fail(*messages):
  print(*messages, file=stderr)
  exit(1)


def output_contact(contact, output):
  if output == 'json':
    print(json.dumps(contact.serialize(), sort_keys=True))
  else:
    value = getattr(contact, output, None)
    print('' if value is None else value)


def main():
  parser = argparse.ArgumentParser(description='List NetBox contacts.')
  parser.add_argument('-o', '--output', choices=OUTPUT_FIELDS, default='name',
                      help='Value to display for each contact (default: name)')
  parser.add_argument('-t', '--tenant', help='Filter by tenant slug')
  parser.add_argument('-T', '--token', help='NetBox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='NetBox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, token=args.token)
  if args.tenant:
    tenant = nb.tenancy.tenants.get(slug=args.tenant)
    if not tenant:
      fail('no such tenant:', args.tenant)

    assignments = nb.tenancy.contact_assignments.filter(
      object_type=TENANT_OBJECT_TYPE,
      object_id=tenant.id,
    )
    contact_ids = {assignment.contact.id for assignment in assignments}
    contacts = nb.tenancy.contacts.filter(id=list(contact_ids)) if contact_ids else []
  else:
    contacts = nb.tenancy.contacts.all()

  for contact in contacts:
    output_contact(contact, args.output)


if __name__ == '__main__':
  main()
