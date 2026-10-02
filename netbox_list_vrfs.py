#!/usr/bin/env python3

import argparse
import os
from sys import exit, stderr

import pynetbox


def fail(*messages):
  print(*messages, file=stderr)
  exit(1)


def main():
  parser = argparse.ArgumentParser(description='List NetBox VRFs.')
  parser.add_argument('-t', '--tenant', help='Filter by tenant slug')
  parser.add_argument('-T', '--token', help='NetBox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='NetBox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, token=args.token)
  if args.tenant:
    tenant = nb.tenancy.tenants.get(slug=args.tenant)
    if not tenant:
      fail('no such tenant:', args.tenant)
    vrfs = nb.ipam.vrfs.filter(tenant_id=tenant.id)
  else:
    vrfs = nb.ipam.vrfs.all()

  for vrf in vrfs:
    print(vrf.name)


if __name__ == '__main__':
  main()
