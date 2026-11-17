#!/usr/bin/env python3

import argparse
import ipaddress
import os
from sys import exit, stderr

import pynetbox


def fail(*messages):
  print(*messages, file=stderr)
  exit(1)


def network(value):
  try:
    return str(ipaddress.ip_network(value))
  except ValueError as error:
    raise argparse.ArgumentTypeError(str(error)) from error


def main():
  parser = argparse.ArgumentParser(description='Find the first available IP in a NetBox prefix without allocating it.')
  parser.add_argument('prefix', type=network, help='IPv4 or IPv6 network in CIDR notation')
  parser.add_argument('-t', '--tenant', help='Filter prefix by tenant slug')
  parser.add_argument('-r', '--vrf', help='Filter prefix by VRF name')
  parser.add_argument('-T', '--token', help='NetBox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='NetBox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, token=args.token)
  filters = {'prefix': args.prefix}
  if args.tenant is not None:
    tenant = nb.tenancy.tenants.get(slug=args.tenant)
    if not tenant:
      fail('no such tenant:', args.tenant)
    filters['tenant_id'] = tenant.id
  if args.vrf is not None:
    vrfs = [vrf for vrf in nb.ipam.vrfs.filter(name=args.vrf) if vrf.name == args.vrf]
    if not vrfs:
      fail('no such VRF:', args.vrf)
    if len(vrfs) > 1:
      fail('VRF name is ambiguous:', args.vrf)
    filters['vrf_id'] = vrfs[0].id

  prefixes = list(nb.ipam.prefixes.filter(**filters))
  if not prefixes:
    fail('no such prefix:', args.prefix)
  if len(prefixes) > 1:
    fail('prefix is ambiguous; select a tenant or VRF:', args.prefix)

  addresses = prefixes[0].available_ips.list(limit=1)
  if not addresses:
    fail('no available IP addresses in prefix:', args.prefix)
  print(addresses[0].address)


if __name__ == '__main__':
  main()
