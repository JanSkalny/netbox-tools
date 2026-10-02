#!/usr/bin/env python3

import json
from decimal import Decimal, InvalidOperation
from sys import exit, stderr


OBJECT_ENDPOINTS = {
  'ip': ('ipam', 'ip_addresses'),
  'prefix': ('ipam', 'prefixes'),
  'tenant': ('tenancy', 'tenants'),
  'vm': ('virtualization', 'virtual_machines'),
  'device': ('dcim', 'devices'),
  'vlan': ('ipam', 'vlans'),
}

RELATED_OBJECT_TYPES = {
  'ipam.ipaddress': 'ip',
  'ipam.ip-address': 'ip',
  'ipam.prefix': 'prefix',
  'tenancy.tenant': 'tenant',
  'virtualization.virtualmachine': 'vm',
  'virtualization.virtual-machine': 'vm',
  'dcim.device': 'device',
  'ipam.vlan': 'vlan',
}


def fail(*messages):
  print(*messages, file=stderr)
  exit(1)


def endpoint_for(nb, object_type):
  app, endpoint = OBJECT_ENDPOINTS[object_type]
  return getattr(getattr(nb, app), endpoint)


def identifier_lookups(object_type, identifier):
  if identifier.isdecimal():
    lookups = [('id', int(identifier))]
  else:
    lookups = []

  natural_keys = {
    'ip': ('address',),
    'prefix': ('prefix',),
    'tenant': ('slug', 'name'),
    'vm': ('name',),
    'device': ('name',),
    'vlan': ('name',),
  }
  lookups.extend((key, identifier) for key in natural_keys[object_type])
  return lookups


def get_object(nb, object_type, identifier):
  endpoint = endpoint_for(nb, object_type)
  for field, value in identifier_lookups(object_type, identifier):
    obj = endpoint.get(**{field: value})
    if obj:
      return obj
  fail('no such %s:' % object_type, identifier)


def get_custom_value(obj, field_slug):
  custom_fields = getattr(obj, 'custom_fields', {})
  if field_slug not in custom_fields:
    fail('no such custom field for object:', field_slug)
  return custom_fields[field_slug]


def display_value(value):
  if value is None:
    return 'null'
  if isinstance(value, bool):
    return str(value).lower()
  if hasattr(value, 'serialize'):
    value = value.serialize()
  if isinstance(value, dict):
    for key in ('slug', 'name', 'address', 'prefix'):
      if value.get(key) is not None:
        return str(value[key])
    if value.get('id') is not None:
      return str(value['id'])
    return json.dumps(value, sort_keys=True)
  if isinstance(value, (list, tuple)):
    return json.dumps([display_value(item) for item in value])
  return str(value)


def custom_field_definition(nb, field_slug):
  field = nb.extras.custom_fields.get(name=field_slug)
  if not field:
    fail('no such custom field:', field_slug)
  return field


def split_values(value):
  try:
    parsed = json.loads(value)
  except (json.JSONDecodeError, TypeError):
    parsed = None
  if isinstance(parsed, list):
    return parsed
  return [item.strip() for item in value.split(',') if item.strip()]


def parse_boolean(value):
  normalized = value.lower()
  if normalized in ('true', 'yes', '1', 'on'):
    return True
  if normalized in ('false', 'no', '0', 'off'):
    return False
  fail('invalid boolean value:', value)


def related_object_type(field):
  related_type = (
    getattr(field, 'related_object_type', None)
    or getattr(field, 'object_type', None)
  )
  if isinstance(related_type, dict):
    related_type = related_type.get('value') or related_type.get('name')
  elif getattr(related_type, 'value', None):
    related_type = related_type.value
  if not related_type:
    return None
  normalized = str(related_type).lower().replace('_', '').replace(' ', '')
  return RELATED_OBJECT_TYPES.get(normalized)


def choice_value(value):
  if isinstance(value, dict):
    return value.get('value')
  if getattr(value, 'value', None) is not None:
    return value.value
  try:
    return value['value']
  except (KeyError, TypeError):
    return value


def related_object_id(nb, field, identifier):
  object_type = related_object_type(field)
  if not object_type:
    fail('custom field does not expose a supported related object type:', field.name)
  return get_object(nb, object_type, str(identifier)).id


def parse_value(nb, field, value):
  field_type = str(choice_value(getattr(field, 'type', 'text'))).lower()
  if field_type == 'integer':
    try:
      return int(value)
    except ValueError:
      fail('invalid integer value:', value)
  if field_type == 'decimal':
    try:
      Decimal(value)
    except InvalidOperation:
      fail('invalid decimal value:', value)
    # JSON has no decimal type; DRF accepts an exact decimal string.
    return value
  if field_type == 'boolean':
    return parse_boolean(value)
  if field_type == 'json':
    try:
      return json.loads(value)
    except json.JSONDecodeError as error:
      fail('invalid JSON value:', error)
  if field_type in ('multiselect', 'multi-select'):
    return split_values(value)
  if field_type == 'object':
    return related_object_id(nb, field, value)
  if field_type in ('multiobject', 'multi-object'):
    return [related_object_id(nb, field, item) for item in split_values(value)]
  return value
