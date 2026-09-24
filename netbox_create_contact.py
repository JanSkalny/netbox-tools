#!/usr/bin/env python3

import argparse
import os

import pynetbox


def main():
  parser = argparse.ArgumentParser(description='Create a NetBox contact.')
  parser.add_argument('-n', '--name', required=True, help='Contact name')
  parser.add_argument('-p', '--phone', help='Contact phone number')
  parser.add_argument('-e', '--email', help='Contact email address')
  parser.add_argument('-d', '--description', help='Contact description')
  parser.add_argument('-T', '--token', help='NetBox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='NetBox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, token=args.token)
  contact_data = {
    'name': args.name,
  }
  for field in ('phone', 'email', 'description'):
    value = getattr(args, field)
    if value is not None:
      contact_data[field] = value

  contact = nb.tenancy.contacts.create(contact_data)
  print(contact.id)


if __name__ == '__main__':
  main()
