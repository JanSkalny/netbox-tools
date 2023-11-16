#!/usr/bin/env python3

from sys import stderr,exit,argv
import json,yaml,os,ipaddress,random,pynetbox,argparse,re
import requests as req
from pprint import pprint
from uuid import uuid4

def fail(*messages):
  print(*messages, file=stderr)
  exit(1)

def warn(*messages):
  print(*messages, file=stderr)

def debug(*messages):
  print(*messages, file=stderr)

parser = argparse.ArgumentParser()
parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
parser.add_argument('-H', '--host', help='Device name.', required=True)
parser.add_argument('-N', '--no-dry-run', help='Don\'t just show changes but also save them to netbox', action='store_true')
args = parser.parse_args()

nb = pynetbox.api(args.api_url, args.token)

dev = nb.dcim.devices.get(name=args.host)
if not dev:
  fail('no such device')

ifaces = nb.dcim.interfaces.filter(device=dev)

for iface in ifaces:
  if iface.count_ipaddresses == 0:
    warn('iface without ip addresses', iface)
    continue

  ip = nb.ipam.ip_addresses.get(interface_id=iface.id)
  if not ip:
    fail('ip address not found on ', iface)

  if not iface.untagged_vlan:
    warn('untagged interface', iface)
    continue

  prefixes = nb.ipam.prefixes.filter(vlan_id=iface.untagged_vlan.id)
  if len(prefixes) == 0:
    fail('no prefixed matched ip', ip)
  if len(prefixes) > 1:
    warning('too many prefixes found. using shortest one')
  prefix = list(prefixes)[-1]

  if iface.description != prefix.description:
    warn('rename', iface, iface.description, '->', prefix.description)
    if args.no_dry_run:
      iface.description = prefix.description
      iface.save()
