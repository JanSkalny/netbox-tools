#!/usr/bin/env python3

import argparse
import os

import pynetbox

from netbox_custom_common import (
  OBJECT_ENDPOINTS,
  custom_field_definition,
  get_custom_value,
  get_object,
  parse_value,
)


def main():
  parser = argparse.ArgumentParser(description='Set one custom field on a NetBox object.')
  parser.add_argument('object_type', choices=OBJECT_ENDPOINTS, help='Object type')
  parser.add_argument('identifier', help='Object ID, slug, name, address, or prefix')
  parser.add_argument('field', help='Custom field slug')
  parser.add_argument('value', nargs='?', help='New value; quote values containing spaces')
  parser.add_argument('--clear', action='store_true', help='Clear the custom field')
  parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  if args.clear == (args.value is not None):
    parser.error('provide either VALUE or --clear')

  nb = pynetbox.api(args.api_url, token=args.token)
  obj = get_object(nb, args.object_type, args.identifier)
  get_custom_value(obj, args.field)
  field = custom_field_definition(nb, args.field)
  value = None if args.clear else parse_value(nb, field, args.value)

  obj.custom_fields[args.field] = value
  obj.save()
  # Echo the CLI representation so related objects remain names/slugs, not IDs.
  print('%s=%s' % (args.field, 'null' if args.clear else args.value))


if __name__ == '__main__':
  main()
