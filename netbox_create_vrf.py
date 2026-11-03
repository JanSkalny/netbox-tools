#!/usr/bin/env python3

import argparse
import os
from sys import exit, stderr

import pynetbox


def fail(*messages):
  print(*messages, file=stderr)
  exit(1)


def vrf_tenant_id(vrf):
  tenant = getattr(vrf, 'tenant', None)
  return getattr(tenant, 'id', tenant)


def main():
  parser = argparse.ArgumentParser(description='Create a NetBox VRF.')
  parser.add_argument('name', help='VRF name')
  parser.add_argument('-t', '--tenant', help='Tenant slug')
  parser.add_argument('-T', '--token', help='NetBox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='NetBox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, token=args.token)
  vrf_data = {'name': args.name}
  tenant_id = None

  if args.tenant:
    tenant = nb.tenancy.tenants.get(slug=args.tenant)
    if not tenant:
      fail('no such tenant:', args.tenant)
    tenant_id = tenant.id
    vrf_data['tenant'] = tenant_id

  duplicate = any(
    vrf.name == args.name and vrf_tenant_id(vrf) == tenant_id
    for vrf in nb.ipam.vrfs.filter(name=args.name)
  )
  if duplicate:
    fail('VRF already exists with the same name under the same tenant:', args.name)

  vrf = nb.ipam.vrfs.create(vrf_data)
  print(vrf.id)


if __name__ == '__main__':
  main()
