#!/usr/bin/env python3

from sys import stderr,exit,argv
import json,yaml,os,ipaddress,random,pynetbox,argparse
import requests as req
from pprint import pprint
from uuid import uuid4

def fail(*messages):
  print(*messages, file=stderr)
  exit(1)

def warn(*messages):
  print(*messages, file=stderr)

parser = argparse.ArgumentParser()
parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
parser.add_argument('-f', '--fqdn', help='VM name', required=True)
parser.add_argument('-p', '--platform', help='New platform', required=True)
parser.add_argument('-n', '--dry-run', help='Dry run', action='store_true')
args = parser.parse_args()

nb = pynetbox.api(args.api_url, args.token)

# find device or vm
vm = nb.virtualization.virtual_machines.get(name=args.fqdn)
dev = nb.dcim.devices.get(name=args.fqdn)
if not dev and not vm:
    fail('no such dev or vm')
host = vm if vm else dev

# find the platform object
platform = nb.dcim.platforms.get(slug=args.platform)
if not platform:
  fail("no such platform")

if host.platform['slug'] != args.platform:
    warn(host, host.platform['slug'], "->", args.platform)
    if not args.dry_run:
        host.platform = platform
        host.save()
else:
    warn(host, "platform is aready", args.platform)
