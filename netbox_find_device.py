#!/usr/bin/env python3

from sys import stderr,exit,argv
import json,yaml,os,ipaddress,random,pynetbox,argparse
import requests as req
from pprint import pprint
from uuid import uuid4

# display error & bail out
def fail(*messages):
  print(*messages, file=stderr)
  exit(1)


doc = """ 
Find device or VM name with specific service name.

## Usage:
%s FQDN

""" % argv[0]


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  parser.add_argument('-u', '--uuid', help='Display UUID custom field instead of name. (defaults to false)', action='store_true')
  parser.add_argument("fqdn")
  args = parser.parse_args()

  FQDN = args.fqdn

  nb = pynetbox.api(args.api_url, args.token)

  # find matching services
  services = nb.ipam.services.filter(name=FQDN, protocol="tcp", port=22)
  if len(services) > 1:
    fail("!! too many matching services")
  if len(services) == 1:
    service = list(services)[0]
    if service['virtual_machine']:
      if args.uuid:
        service.virtual_machine.full_details()
        print(f'{service["virtual_machine"]["custom_fields"]["uuid"]}')
      else:
        print(service['virtual_machine']['name'])
    elif service['device']:
      if args.uuid:
        fail("!! devices don't have uuids")
      print(service['device']['name'])
    else:
      fail('!! service without parent')
    exit(0)

  # find ips with maching fqdn
  ips = nb.ipam.ip_addresses.filter(dns_name=FQDN)
  #if len(ips) > 1:
  #  fail("!! too many matching ips")
  if len(ips) >= 1:
    ip = list(ips)[0]
    if not ip['assigned_object']:
      fail('!! object not assigned to ip', ip)
    if 'virtual_machine' in ip['assigned_object']:
      if args.uuid:
        ip.assigned_object.virtual_machine.full_details()
        print(f'{ip["assigned_object"]["virtual_machine"]["custom_fields"]["uuid"]}')
      else:
        print(ip['assigned_object']['virtual_machine']['name'])
    elif 'device' in ip['assigned_object']:
      if args.uuid:
        fail("!! devices don't have uuids")
      else:
        print(ip['assigned_object']['device']['name'])
    else:
      fail('!! ip without parent', ip)
    exit(0)

  fail("not found")
 

if __name__ == "__main__":
  main()
