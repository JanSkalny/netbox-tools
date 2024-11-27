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
parser.add_argument('-N', '--no-dry-run', help='Don\'t just show changes but also save them to netbox', action='store_true')
args = parser.parse_args()

nb = pynetbox.api(args.api_url, args.token)

vm_ifaces = nb.virtualization.interfaces.all()
dev_ifaces = nb.dcim.interfaces.all()
for iface in vm_ifaces:

    # load primary ip 
    iface.virtual_machine.full_details()
    ip = iface.virtual_machine.primary_ip4
    ip.full_details()

    # determine name consistency
    ifname = iface.virtual_machine.name
    ipname = ip.dns_name
    if ifname != ipname:
        warn(iface.virtual_machine.name, "rename", iface.name, ip.display, ipname, '->', ifname)
        if args.no_dry_run:
            ip.dns_name = ifname
            ip.save()
    else:
        debug(iface.virtual_machine.name, "is consistent")

