#!/usr/bin/env python3

import argparse
import os
from sys import exit, stderr

import pynetbox

from netbox_custom_common import custom_field_value


def fail(*messages):
  print(*messages, file=stderr)
  exit(1)


def output_vm(vm, uuid, full_details=False):
  if uuid:
    if full_details:
      vm.full_details()
    print(custom_field_value(vm['custom_fields']['uuid']))
  else:
    print(vm['name'])


def main():
  parser = argparse.ArgumentParser(description='Find a VM by name, TCP/22 service name, or IP DNS name.')
  parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  parser.add_argument('-u', '--uuid', help='Display UUID custom field instead of name. (defaults to false)', action='store_true')
  parser.add_argument('fqdn')
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, args.token)

  vm = nb.virtualization.virtual_machines.get(name=args.fqdn)
  if vm:
    output_vm(vm, args.uuid)
    return

  services = nb.ipam.services.filter(name=args.fqdn, protocol='tcp', port=22)
  if len(services) > 1:
    fail('!! too many matching services')
  if len(services) == 1:
    service = list(services)[0]
    if not service['virtual_machine']:
      fail('!! service without VM')
    output_vm(service['virtual_machine'], args.uuid, full_details=True)
    return

  ips = nb.ipam.ip_addresses.filter(dns_name=args.fqdn)
  if len(ips) >= 1:
    ip = list(ips)[0]
    if not ip['assigned_object']:
      fail('!! object not assigned to ip', ip)
    if 'virtual_machine' not in ip['assigned_object'] or not ip['assigned_object']['virtual_machine']:
      fail('!! ip without VM', ip)
    output_vm(ip['assigned_object']['virtual_machine'], args.uuid, full_details=True)
    return

  fail('not found')


if __name__ == '__main__':
  main()
