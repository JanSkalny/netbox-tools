#!/usr/bin/env python3

import argparse
import os
from sys import exit, stderr

import pynetbox

from netbox_filter_common import add_filter_argument, filter_endpoint, has_exact_filter


def fail(*messages):
  print(*messages, file=stderr)
  exit(1)

def warn(*messages):
  print(*messages, file=stderr)

def main():
  parser = argparse.ArgumentParser(description='List NetBox virtual machine FQDNs.')
  parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  parser.add_argument('-t', '--tenant', help='Tenant name (defaults to NETBOX_DEFAULT_TENANT env)', default=os.getenv('NETBOX_DEFAULT_TENANT'))
  parser.add_argument('-c', '--cluster', help='Fitler by cluster name')
  parser.add_argument('-s', '--status', help='Fitler by status (eg. "decommissioning", defaults to "active")', default='active')
  add_filter_argument(parser)
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, args.token)

  vms = filter_endpoint(
    nb,
    parser,
    nb.virtualization.virtual_machines,
    args.filter,
  )
  status_filtered_by_api = has_exact_filter(args.filter, 'status')
  for vm in vms:
    if not status_filtered_by_api and vm.status.value != args.status:
      continue
    # filtering vms by cluster
    if args.cluster and vm.cluster['name'] != args.cluster:
      continue

    print(vm.custom_fields['fqdn'])


if __name__ == '__main__':
  main()
