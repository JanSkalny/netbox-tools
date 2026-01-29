#!/usr/bin/env python3

from sys import stderr,exit,argv
import json,yaml,os,ipaddress,random,pynetbox,argparse,ast
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
parser.add_argument('-c', '--cluster', help='Cluster name', required=True)
parser.add_argument('--short-uuids', help='Use short UUIDs (defaults to NETBOX_SHORT_UUIDS env or False)', default=ast.literal_eval(os.getenv('NETBOX_SHORT_UUIDS', 'False')), action='store_true')
args = parser.parse_args()

nb = pynetbox.api(args.api_url, args.token)

# fetch all vms from cluster
vms = nb.virtualization.virtual_machines.filter(cluster = args.cluster)
mps = []
for vm in vms:
    #if vm.status != 'Active':
    #    warn
    wwid = None
    if 'storage_wwn' in vm.custom_fields:
        wwid = vm.custom_fields['storage_wwn']
        if not wwid or len(wwid) == 0:
            fail(vm, "empty storage_wwn")
        wwid = "3" + wwid.replace(':','').lower()
    if 'storage_wwid' in vm.custom_fields:
        wwid = vm.custom_fields['storage_wwid']
        if not wwid or len(wwid) == 0:
            fail(vm, "empty storage_wwid")

    if not wwid:
        fail(vm, "missing wwid")

    uuid = vm.custom_fields['uuid']
    if args.short_uuids:
      uuid = uuid.split('-')[0]

    mps.append({
        'name': f"vm-{uuid}",
        'wwid': wwid,
        })

mps.sort(key=lambda x: x['name'])

print("# generated from netbox. do not change manually")
if len(mps) == 0:
    print("multipath: []")
else:
    print("multipath:")
    for mp in mps:
        print(" - name:", mp['name'])
        print("   wwid:", mp['wwid'])
