#!/usr/bin/env python3

import argparse
import os
from sys import exit, stderr

import pynetbox

from netbox_custom_common import custom_field_value
from netbox_filter_common import add_filter_argument, filter_endpoint, has_exact_filter


def fail(*messages):
  print(*messages, file=stderr)
  exit(1)

def warn(*messages):
  print(*messages, file=stderr)

def main():
  parser = argparse.ArgumentParser(description='List NetBox virtual machines.')
  parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  parser.add_argument('-t', '--tenant', help='Filter by tenant name')
  parser.add_argument('-c', '--cluster', help='Fitler by cluster name')
  parser.add_argument('-s', '--status', help='Fitler by status (eg. "decommissioning", defaults to "active")', default='active')
  parser.add_argument('-u', '--uuid', help='Display "vm-UUID" instead of name (defaults to false)', action='store_true')
  parser.add_argument('-x', '--silent', help='Don\'t show skip messages (defaults to false)', action='store_true')
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
    skip = []

    # filtering vms by status
    if not status_filtered_by_api and vm.status.value != args.status:
      skip.append(f"status {vm.status}")

    # filter vms by tenant
    if args.tenant and vm.tenant and vm.tenant.name != args.tenant:
      skip.append(f"tenant {vm.tenant.name}")

    # filtering vms by cluster
    if args.cluster:
      if not vm.cluster:
        skip.append("not a cluster vm")
      elif vm.cluster.name != args.cluster:
        skip.append(f"cluster {vm.cluster}")

    if len(skip) > 0:
      if not args.silent:
        for s in skip:
          warn("# skip", vm.name, s)
      continue

    if args.uuid:
      print(f'vm-{custom_field_value(vm.custom_fields["uuid"])}')
    else:
      print(vm.name)


if __name__ == '__main__':
  main()
