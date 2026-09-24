#!/usr/bin/env python3

import argparse
import os

import pynetbox


parser = argparse.ArgumentParser()
parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
parser.add_argument('--names', action='store_true', help='Display tenant names instead of slugs')
args = parser.parse_args()

nb = pynetbox.api(args.api_url, args.token)

# fetch all tenants
tenants = nb.tenancy.tenants.all()
for tenant in tenants:
  print(tenant.name if args.names else tenant.slug)
