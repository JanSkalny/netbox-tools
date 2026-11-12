#!/usr/bin/env python3

import argparse
import csv
import os
import sys

import pynetbox


TENANT_OBJECT_TYPE = 'tenancy.tenant'


def main():
  parser = argparse.ArgumentParser(description='List NetBox tenant contact assignments as TSV.')
  parser.add_argument('-t', '--tenant', help='Filter by tenant slug')
  parser.add_argument('-c', '--contact', help='Filter by contact ID or exact name (contacts have no slug)')
  parser.add_argument('-T', '--token', help='NetBox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='NetBox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, token=args.token)
  filters = {'object_type': TENANT_OBJECT_TYPE}
  tenants = {}
  if args.tenant:
    tenant = nb.tenancy.tenants.get(slug=args.tenant)
    if not tenant:
      parser.error('no such tenant: ' + args.tenant)
    filters['object_id'] = tenant.id
    tenants[tenant.id] = tenant

  if args.contact:
    if args.contact.isdecimal():
      contact = nb.tenancy.contacts.get(id=int(args.contact))
      contacts = [contact] if contact else []
    else:
      contacts = list(nb.tenancy.contacts.filter(name=args.contact))
    if not contacts:
      parser.error('no such contact: ' + args.contact)
    if len(contacts) > 1:
      parser.error('multiple contacts found; use a contact ID: ' + args.contact)
    filters['contact_id'] = contacts[0].id

  writer = csv.writer(sys.stdout, delimiter='\t', lineterminator='\n')
  writer.writerow(('id', 'tenant', 'role'))
  for assignment in nb.tenancy.contact_assignments.filter(**filters):
    if assignment.object_id not in tenants:
      tenants[assignment.object_id] = nb.tenancy.tenants.get(id=assignment.object_id)
    tenant = tenants[assignment.object_id]
    writer.writerow((
      assignment.contact.id,
      getattr(tenant, 'slug', ''),
      getattr(assignment.role, 'slug', ''),
    ))


if __name__ == '__main__':
  main()
