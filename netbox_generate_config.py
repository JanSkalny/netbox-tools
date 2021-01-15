#!/usr/bin/env python3

from sys import argv,stderr,exit
import json, os, yaml, pynetbox, re, ipaddress
from collections import defaultdict
from pprint import pprint

doc = """ 
Get config context from netbox for specified device.

## Usage
%s "FQDN" 

""" % (argv[0])

def assume_ip_gateway(network):
  return str(ipaddress.ip_network(network,False)[1]).split('/')[0]

def warn(*msg):
  print(*msg, file=stderr)

def fail(*msg):
  print(*msg, file=stderr)
  exit(1)

if len(argv) != 2:
  fail("error, invalid number of args!", doc)

FQDN = argv[1] 

nb = pynetbox.api(os.getenv('NETBOX_API_URL'), token=os.getenv('NETBOX_TOKEN'))

dev = None
vm = None

# find vm or device object
vm = nb.virtualization.virtual_machines.get(name=FQDN)
dev = nb.dcim.devices.get(name=FQDN)

if vm is None and dev is None:
  fail("no such device or vm")

if vm and dev:
  fail("make up your mind. conflicting naming detected!")

obj = vm if vm else dev

print("# generated from netbox. do not change manually")
print(yaml.dump(obj['config_context']))
