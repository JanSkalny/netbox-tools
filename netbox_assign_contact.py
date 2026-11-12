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
    description='Assign a NetBox contact to a tenant unless that assignment already exists.',
    usage='%(prog)s [options] [--email EMAIL | --phone PHONE | CONTACT_ID] TENANT [ROLE]',
  )
  parser.add_argument('targets', nargs='+', metavar='TARGET',
                      help='Contact ID (unless --email or --phone is used), tenant slug, optional role slug')
  selector = parser.add_mutually_exclusive_group()
  selector.add_argument('--email', help='Exact contact email')
  selector.add_argument('--phone', help='Exact contact phone')
  parser.add_argument('-a', '--append', action='store_true',
                      help='Allow another assignment with a different role')
  parser.add_argument('-n', '--dry-run', action='store_true',
                      help='Show whether an assignment would be created without saving')
  parser.add_argument('-T', '--token', help='NetBox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='NetBox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  field = 'email' if args.email is not None else 'phone' if args.phone is not None else None
  targets = list(args.targets)
  if field is None:
    if len(targets) not in (2, 3):
      parser.error('provide CONTACT_ID TENANT [ROLE], or use --email or --phone with TENANT [ROLE]')
    try:
      contact_id = int(targets.pop(0))
    except ValueError:
      parser.error('CONTACT_ID must be an integer')
  elif len(targets) not in (1, 2):
    parser.error('with --email or --phone, provide TENANT [ROLE]')
  tenant_slug = targets[0]
  role_slug = targets[1] if len(targets) == 2 else None

  nb = pynetbox.api(args.api_url, token=args.token)

  if field is None:
    contact = nb.tenancy.contacts.get(id=contact_id)
    if not contact:
      fail('no such contact:', contact_id)
  else:
    value = getattr(args, field)
    contacts = list(nb.tenancy.contacts.filter(**{field: value}))
    if not contacts:
      fail('no such contact:', field, value)
    if len(contacts) > 1:
      fail('multiple contacts found:', field, value)
    contact = contacts[0]

  tenant = nb.tenancy.tenants.get(slug=tenant_slug)
  if not tenant:
    fail('no such tenant:', tenant_slug)

  role = None
  if args.append and role_slug is not None:
    role = nb.tenancy.contact_roles.get(slug=role_slug)
    if not role:
      fail('no such contact role:', role_slug)

  assignments = nb.tenancy.contact_assignments.filter(
    contact_id=contact.id,
    object_type=TENANT_OBJECT_TYPE,
    object_id=tenant.id,
  )
  for assignment in assignments:
    if args.append:
      existing_role_id = assignment.role.id if assignment.role is not None else None
      if existing_role_id != (role.id if role is not None else None):
        continue
    if args.dry_run:
      print(f'no change: assignment {assignment.id} already exists (dry run)')
    else:
      print(assignment.id)
    return

  assignment_data = {
    'object_type': TENANT_OBJECT_TYPE,
    'object_id': tenant.id,
    'contact': contact.id,
  }
  if role_slug is not None:
    if role is None:
      role = nb.tenancy.contact_roles.get(slug=role_slug)
    if not role:
      fail('no such contact role:', role_slug)
    assignment_data['role'] = role.id

  if args.dry_run:
    print(f'would create assignment: contact {contact.id}, tenant {tenant_slug}, '
          f'role {role_slug if role_slug is not None else "(none)"} (dry run)')
    return

  assignment = nb.tenancy.contact_assignments.create(assignment_data)
  print(assignment.id)


if __name__ == '__main__':
  main()
