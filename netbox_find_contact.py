#!/usr/bin/env python3

import argparse
import json
import os
from sys import exit, stderr

import pynetbox


OUTPUT_FIELDS = ('name', 'phone', 'email', 'id', 'json')


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
  parser = argparse.ArgumentParser(description='Find a NetBox contact by exact name, phone, or email.')
  parser.add_argument('value', help='Exact contact name, phone, or email')
  parser.add_argument('-o', '--output', choices=OUTPUT_FIELDS, default='id',
                      help='Value to display (default: id)')
  parser.add_argument('-T', '--token', help='NetBox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='NetBox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, token=args.token)
  contacts_by_id = {}
  for field in ('name', 'phone', 'email'):
    for contact in nb.tenancy.contacts.filter(**{field: args.value}):
      contacts_by_id[contact.id] = contact
  contacts = list(contacts_by_id.values())

  if not contacts:
    fail('no such contact:', args.value)
  if len(contacts) > 1:
    fail('multiple contacts found:', args.value)

  output_contact(contacts[0], args.output)


if __name__ == '__main__':
  main()
