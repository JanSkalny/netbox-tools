#!/usr/bin/env python3

import argparse
import os

import pynetbox

from netbox_custom_common import OBJECT_ENDPOINTS, display_value, get_custom_value, get_object


def main():
  parser = argparse.ArgumentParser(description='List custom fields on a NetBox object.')
  parser.add_argument('object_type', choices=OBJECT_ENDPOINTS, help='Object type')
  parser.add_argument('identifier', help='Object ID, slug, name, address, or prefix')
  parser.add_argument('field', nargs='?', help='Optional custom field slug')
  parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, token=args.token)
  obj = get_object(nb, args.object_type, args.identifier)
  if args.field:
    fields = [(args.field, get_custom_value(obj, args.field))]
  else:
    fields = sorted(getattr(obj, 'custom_fields', {}).items())

  for slug, value in fields:
    print('%s\t%s' % (slug, display_value(value)))


if __name__ == '__main__':
  main()
