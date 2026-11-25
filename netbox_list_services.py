#!/usr/bin/env python3

import argparse
import csv
from ipaddress import ip_interface
from itertools import product
import json
import os
import sys

import pynetbox

from netbox_filter_common import choice_value


TABLE_FIELDS = ('id', 'parent_type', 'parent', 'service', 'port_mappings', 'ip_addresses')


def parse_port_mapping(value):
  protocol, _, port = value.lower().partition('/')
  if protocol not in ('tcp', 'udp', 'sctp') or not port.isascii() or not port.isdecimal():
    raise argparse.ArgumentTypeError('expected protocol/port, e.g. tcp/22')
  try:
    number = int(port)
  except ValueError:
    raise argparse.ArgumentTypeError('port must be between 1 and 65535') from None
  if not 1 <= number <= 65535:
    raise argparse.ArgumentTypeError('port must be between 1 and 65535')
  return protocol, number


def parse_ip(value):
  try:
    address = ip_interface(value)
  except ValueError:
    raise argparse.ArgumentTypeError('expected an IPv4 or IPv6 address with an optional prefix length') from None
  return str(address) if '/' in value else str(address.ip)


def parse_parent_id(value):
  try:
    parent_id = int(value)
  except ValueError:
    raise argparse.ArgumentTypeError('expected a positive NetBox object ID') from None
  if parent_id < 1:
    raise argparse.ArgumentTypeError('expected a positive NetBox object ID')
  return parent_id


def port_mappings(service):
  # Avoid a detail request when older servers omit this field from list results.
  mappings = vars(service).get('port_mappings')
  if mappings is not None:
    return mappings
  protocol = choice_value(service.protocol)
  return [f'{protocol}/{port}' for port in service.ports]


def matching_services(nb, args):
  ip_filter = {}
  if args.ip is not None:
    ip_ids = [ip.id for ip in nb.ipam.ip_addresses.filter(address=args.ip)]
    if not ip_ids:
      return
    ip_filter['ip_address_id'] = ip_ids

  parent_filters = [{}]
  if args.fqdn is not None:
    parent_filters = [{'device': args.fqdn}, {'virtual_machine': args.fqdn}]
  elif args.device_id is not None:
    parent_filters = [{'device_id': args.device_id}]
  elif args.vm_id is not None:
    parent_filters = [{'virtual_machine_id': args.vm_id}]

  # Keep each protocol and port together so older NetBox releases can filter them too.
  port_filters = [
    {'protocol': protocol, 'port': port} for protocol, port in dict.fromkeys(args.port)
  ] or [{}]
  endpoint = nb.ipam.services
  seen = set()
  for parent_filter, port_filter in product(parent_filters, port_filters):
    filters = {**parent_filter, **ip_filter, **port_filter}
    services = endpoint.filter(**filters) if filters else endpoint.all()
    for service in services:
      if service.id in seen:
        continue
      seen.add(service.id)
      yield service


def service_row(service):
  parent_fields = vars(service.parent) if service.parent is not None else {}
  return {
    'id': service.id,
    'parent_type': service.parent_object_type,
    'parent': parent_fields.get('name') or parent_fields.get('display', ''),
    'service': service.name,
    'port_mappings': port_mappings(service),
    'ip_addresses': [ip.address for ip in service.ipaddresses],
  }


def main():
  parser = argparse.ArgumentParser(description='List NetBox application services.')
  parent = parser.add_mutually_exclusive_group()
  parent.add_argument('--fqdn', '-H', '--host', help='Filter by exact device or VM name')
  parent.add_argument('--device-id', type=parse_parent_id, metavar='ID', help='Filter by device ID')
  parent.add_argument('--vm-id', type=parse_parent_id, metavar='ID', help='Filter by VM ID')
  parser.add_argument('-i', '--ip', type=parse_ip, metavar='ADDRESS',
                      help='Filter by an explicitly bound IPv4 or IPv6 address, optionally with prefix length')
  parser.add_argument('-p', '--port', '--port-mapping', action='append', type=parse_port_mapping,
                      default=[], metavar='PROTOCOL/PORT', help='Match any supplied mapping (repeatable)')
  parser.add_argument('-o', '--output', choices=('json', 'tsv', 'service-name'), default='service-name',
                      help='Output format (default: service-name)')
  parser.add_argument('-T', '--token', default=os.getenv('NETBOX_TOKEN'),
                      help='NetBox API token (defaults to NETBOX_TOKEN env)')
  parser.add_argument('-A', '--api-url', default=os.getenv('NETBOX_API_URL'),
                      help='NetBox API URL (defaults to NETBOX_API_URL env)')
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, token=args.token)
  services = matching_services(nb, args)
  if args.output == 'service-name':
    for service in services:
      print(service.name)
  elif args.output == 'json':
    print(json.dumps([service_row(service) for service in services], ensure_ascii=False))
  else:
    writer = csv.DictWriter(sys.stdout, fieldnames=TABLE_FIELDS, delimiter='\t', lineterminator='\n')
    writer.writeheader()
    for service in services:
      row = service_row(service)
      row['port_mappings'] = ','.join(row['port_mappings'])
      row['ip_addresses'] = ','.join(row['ip_addresses'])
      writer.writerow(row)


if __name__ == '__main__':
  main()
