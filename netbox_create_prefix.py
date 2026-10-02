#!/usr/bin/env python3

import argparse
import ipaddress
import os
from sys import exit, stderr

import pynetbox


def fail(*messages):
  print(*messages, file=stderr)
  exit(1)


def vlan_number(value):
  number = int(value)
  if number not in range(1, 4095):
    raise argparse.ArgumentTypeError('VLAN number must be between 1 and 4094')
  return number


def cidr(value):
  try:
    return str(ipaddress.ip_network(value, strict=True))
  except ValueError as error:
    raise argparse.ArgumentTypeError(str(error)) from error


def find_vrf(nb, identifier):
  matches = [
    vrf for vrf in nb.ipam.vrfs.all()
    if vrf.name == identifier or getattr(vrf, 'slug', None) == identifier
  ]
  if not matches:
    fail('no such VRF:', identifier)
  if len(matches) > 1:
    fail('VRF identifier is ambiguous:', identifier)
  return matches[0]


def main():
  parser = argparse.ArgumentParser(description='Create a NetBox prefix.')
  parser.add_argument('cidr', type=cidr, help='IPv4 or IPv6 prefix in CIDR notation')
  parser.add_argument('tenant', help='Tenant slug')
  parser.add_argument('-d', '--description', help='Prefix description')
  parser.add_argument('-v', '--vlan', type=vlan_number, help='VLAN number')
  parser.add_argument('-r', '--vrf', help='VRF name (or slug when available)')
  parser.add_argument('-g', '--tag', action='append', default=[], help='Existing tag slug (may be repeated)')
  parser.add_argument('-T', '--token', help='NetBox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='NetBox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, token=args.token)

  tenant = nb.tenancy.tenants.get(slug=args.tenant)
  if not tenant:
    fail('no such tenant:', args.tenant)

  prefix_data = {
    'prefix': args.cidr,
    'tenant': tenant.id,
  }

  if args.description is not None:
    prefix_data['description'] = args.description

  if args.vlan is not None:
    vlans = list(nb.ipam.vlans.filter(vid=args.vlan))
    if not vlans:
      fail('no such VLAN:', args.vlan)
    if len(vlans) > 1:
      fail('multiple VLANs use this number:', args.vlan)
    prefix_data['vlan'] = vlans[0].id

  if args.vrf is not None:
    prefix_data['vrf'] = find_vrf(nb, args.vrf).id

  if args.tag:
    tags = []
    for tag_slug in args.tag:
      tag = nb.extras.tags.get(slug=tag_slug)
      if not tag:
        fail('no such tag:', tag_slug)
      tags.append(tag.id)
    prefix_data['tags'] = tags

  prefix = nb.ipam.prefixes.create(prefix_data)
  print(prefix.id)


if __name__ == '__main__':
  main()
