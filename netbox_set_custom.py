#!/usr/bin/env python3

import argparse
import os

import pynetbox

from netbox_custom_common import (
  OBJECT_ENDPOINTS,
  choice_value,
  custom_field_value,
  custom_field_definition,
  get_custom_value,
  get_object,
  parse_value,
)


def current_choice_values(field, value):
  field_type = str(choice_value(getattr(field, 'type', 'text'))).lower()
  if field_type in ('multiselect', 'multi-select'):
    return custom_field_value(value), None
  if field_type not in ('choice', 'select', 'selection'):
    return value, None
  if isinstance(value, dict) and 'value' in value:
    return value.get('value'), value.get('label')
  if getattr(value, 'value', None) is not None:
    return value.value, getattr(value, 'label', None)
  return value, None


def main():
  parser = argparse.ArgumentParser(description='Set one custom field on a NetBox object.')
  parser.add_argument('object_type', choices=OBJECT_ENDPOINTS, help='Object type')
  parser.add_argument('identifier', help='Object ID, slug, name, address, or prefix')
  parser.add_argument('field', help='Custom field slug')
  parser.add_argument('value', nargs='?', help='New value; quote values containing spaces')
  parser.add_argument('--clear', action='store_true', help='Clear the custom field')
  parser.add_argument('-n', '--dry-run', action='store_true',
                      help='Do not change anything in NetBox; only show the requested change')
  parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  if args.clear == (args.value is not None):
    parser.error('provide either VALUE or --clear')

  nb = pynetbox.api(args.api_url, token=args.token)
  obj = get_object(nb, args.object_type, args.identifier)
  current_value = get_custom_value(obj, args.field)
  field = custom_field_definition(nb, args.field)
  value = None if args.clear else parse_value(nb, field, args.value)
  current_value, current_label = current_choice_values(field, current_value)

  if value == current_value or (current_label is not None and value == current_label):
    print(f"{args.field}: no change")
  else:
    if not args.dry_run:
      print(f"{args.field}: {current_value} -> {value}")
      # PATCH only the requested custom field. Calling save() after mutating
      # custom_fields can resend expanded values for unrelated choice fields
      # (for example, {"value": "24", "label": "24/7"}), which NetBox
      # rejects because it expects the raw choice value.
      obj.update({'custom_fields': {args.field: value}})
    else:
      print(f"{args.field}: {current_value} -> {value} (not saving during dry run)")


if __name__ == '__main__':
  main()
