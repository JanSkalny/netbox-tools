#!/usr/bin/env python3

import argparse
import json
import os

import pynetbox


OUTPUT_FIELDS = ('name', 'phone', 'email', 'id', 'json')


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
  parser.add_argument('-T', '--token', help='NetBox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='NetBox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, token=args.token)
  for contact in nb.tenancy.contacts.all():
    output_contact(contact, args.output)


if __name__ == '__main__':
  main()
