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
parser.add_argument('-t', '--tenant', help='Tenant name (defaults to NETBOX_DEFAULT_TENANT env)', default=os.getenv('NETBOX_DEFAULT_TENANT'))
parser.add_argument('-s', '--site', help='Site name (eg. \'dc\')')
parser.add_argument('-N', '--no-dry-run', help='Don\'t just show changes but also save them to netbox', action='store_true')
parser.add_argument('-X', '--show-candidates', help='Show name candidates and exit without doint anything.', action='store_true')
args = parser.parse_args()

# get all VLANs
nb = pynetbox.api(args.api_url, args.token)
vlans = nb.ipam.vlans.all()

nets = nb.ipam.prefixes.all()
for net in nets:
  if not net.vlan:
    warn('!! network without vlan', net)

for vlan in vlans:
  # filtering functionality
  if args.site:
    if not vlan.site:
      warn('!! vlan without site', vlan.vid, vlan)
      continue
    if args.site.lower() != vlan.site.slug.lower():
      #debug('skip', vlan.name, 'because of site filter', vlan.site, args.site)
      continue
  if args.tenant:
    if not vlan.tenant:
      warn('!! vlan without tenant', vlan.vid, vlan)
      continue
    if args.tenant.lower() != vlan.tenant.slug.lower():
      #debug('skip', vlan.name, 'because of tenant filter', vlan.tenant, args.tenant)
      continue

  net = nb.ipam.prefixes.get(vlan_vid=vlan.vid)
  if not net:
    warn('!! no network associated with vlan', vlan.vid, vlan)
    continue

  if vlan.name != net.description:
    warn('rename',net,net.description,'->',vlan.name)
    if args.no_dry_run:
      net.description = vlan.name
      net.save()
