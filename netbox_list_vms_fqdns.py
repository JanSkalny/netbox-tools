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
parser.add_argument('-t', '--tenant', help='Tenant name (defaults to NETBOX_DEFAULT_TENANT env)', default=os.getenv('NETBOX_DEFAULT_TENANT'))
parser.add_argument('-c', '--cluster', help='Fitler by cluster name')
parser.add_argument('-s', '--status', help='Fitler by status (eg. "decommissioning", defaults to "active")', default='active')
args = parser.parse_args()

nb = pynetbox.api(args.api_url, args.token)

# fetch all vms
vms = nb.virtualization.virtual_machines.all()
ids = {}
for vm in vms:
  if vm.status.value != args.status:
    continue
  # filtering vms by cluster
  if args.cluster and vm.cluster['name'] != args.cluster:
    continue

  print(vm.custom_fields['fqdn'])
