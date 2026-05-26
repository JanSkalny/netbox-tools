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
parser.add_argument('-w', '--wwid', help='New wwid', required=True)
parser.add_argument('-n', '--dry-run', help='Dry run', action='store_true')
args = parser.parse_args()

nb = pynetbox.api(args.api_url, args.token)

vm = nb.virtualization.virtual_machines.get(name=args.fqdn)
if not(vm):
    fail('no such vm')

if vm['custom_fields']['storage_wwid'] != args.wwid:
    warn(vm, vm['custom_fields']['storage_wwid'], "->", args.wwid)
    if not args.dry_run:
        vm['custom_fields']['storage_wwid'] = args.wwid
        vm.save()
else:
    warn(vm, "wwid is aready", args.wwid)

