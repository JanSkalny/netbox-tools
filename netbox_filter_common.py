import argparse


def filter_argument(value):
  key, separator, filter_value = value.partition('=')
  if not separator or not key:
    raise argparse.ArgumentTypeError('filters must use KEY=VALUE format')
  return key, filter_value


def add_filter_argument(parser):
  parser.add_argument(
    '--filter',
    action='append',
    default=[],
    type=filter_argument,
    metavar='KEY=VALUE',
    help='Filter using a NetBox API parameter; repeat to combine filters',
  )


def has_exact_filter(requested_filters, key):
  return any(filter_key == key for filter_key, _ in requested_filters)


def choice_value(value):
  if isinstance(value, dict):
    return value.get('value')
  return getattr(value, 'value', value)


def custom_field_filter(nb, parser, key, value):
  if not key.startswith('cf_'):
    return None

  field_name, separator, lookup = key[3:].rpartition('__')
  if not separator:
    field_name = key[3:]
    lookup = None

  field = nb.extras.custom_fields.get(name=field_name)
  if not field:
    parser.error(f'no such custom field: {field_name}')

  filter_logic = str(choice_value(getattr(field, 'filter_logic', ''))).lower()
  if filter_logic == 'disabled':
    parser.error(f'filtering is disabled for custom field: {field_name}')

  field_type = str(choice_value(getattr(field, 'type', ''))).lower()
  if field_type == 'boolean':
    normalized = value.lower()
    if normalized in ('true', 'yes', '1', 'on'):
      value = 'true'
    elif normalized in ('false', 'no', '0', 'off'):
      value = 'false'
    else:
      parser.error(f'invalid boolean value for {field_name}: {value}')

  return field_name, field_type, lookup, value


def comparable_custom_field_value(field_type, value):
  if field_type == 'boolean':
    return value == 'true'
  return value


def custom_field_value_matches(actual, expected):
  if isinstance(actual, (list, tuple)):
    return any(custom_field_value_matches(item, expected) for item in actual)

  actual = choice_value(actual)
  if actual is None:
    return False
  if isinstance(expected, bool):
    return actual is expected
  return str(actual) == expected


def is_excluded_by_custom_field_negation(record, negated_filters):
  custom_fields = getattr(record, 'custom_fields', {}) or {}
  return any(
    custom_field_value_matches(custom_fields.get(field_name), excluded_value)
    for field_name, excluded_value in negated_filters
  )


def add_filter(filters, key, value):
  if key not in filters:
    filters[key] = value
  elif isinstance(filters[key], list):
    filters[key].append(value)
  else:
    filters[key] = [filters[key], value]


def filter_endpoint(nb, parser, endpoint, requested_filters, base_filters=None):
  filters = dict(base_filters or {})
  negated_custom_field_filters = []

  for key, value in requested_filters:
    custom_filter = custom_field_filter(nb, parser, key, value)
    if not custom_filter:
      add_filter(filters, key, value)
      continue

    field_name, field_type, lookup, value = custom_filter
    if lookup == 'n':
      negated_custom_field_filters.append((
        field_name,
        comparable_custom_field_value(field_type, value),
      ))
    else:
      add_filter(filters, key, value)

  records = endpoint.filter(**filters) if filters else endpoint.all()
  if not negated_custom_field_filters:
    return records
  return (
    record for record in records
    if not is_excluded_by_custom_field_negation(
      record,
      negated_custom_field_filters,
    )
  )
