#!/usr/bin/env python3

import argparse
import os
from sys import exit, stderr

import pynetbox


def main():
  parser = argparse.ArgumentParser(description='Update an existing NetBox contact.')
  parser.add_argument('contact_id', type=int, help='Contact ID')
  parser.add_argument('--name', help='New contact name')
  parser.add_argument('--description', help='New contact description')
  parser.add_argument('--email', help='New contact email address')
  parser.add_argument('--phone', help='New contact phone number')
  parser.add_argument('-n', '--dry-run', action='store_true', help='Show changes without saving')
  parser.add_argument('-Z', '--no-empty', action='store_true', help='Skip changes that would clear non-empty fields')
  parser.add_argument('-T', '--token', help='NetBox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='NetBox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  update_data = {
    field: getattr(args, field)
    for field in ('name', 'description', 'email', 'phone')
    if getattr(args, field) is not None
  }
  if not update_data:
    parser.error('at least one of --name, --description, --email, and --phone is required')

  nb = pynetbox.api(args.api_url, token=args.token)
  contact = nb.tenancy.contacts.get(id=args.contact_id)
  if not contact:
    print('no such contact:', args.contact_id, file=stderr)
    exit(1)

  if args.no_empty:
    update_data = {
      field: value for field, value in update_data.items()
      if value != '' or not getattr(contact, field, '')
    }

  update_data = {
    field: value for field, value in update_data.items()
    if getattr(contact, field, '') != value
  }
  if not update_data:
    return

  changes = [
    f'{field}: {getattr(contact, field, "")!r} -> {value!r}'
    for field, value in update_data.items()
  ]
  if not args.dry_run:
    contact.update(update_data)
  for change in changes:
    print(change + (' (dry run)' if args.dry_run else ''))


if __name__ == '__main__':
  main()
