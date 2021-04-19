#!/usr/bin/env python3

from sys import argv,stderr,exit
import json, os, yaml, pynetbox, re, ipaddress
from collections import defaultdict
from pprint import pprint

doc = """ 
Generate virtual configuration from netbox.

## Usage
%s "NAME" 

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

NAME = argv[1] 

nb = pynetbox.api(os.getenv('NETBOX_API_URL'), token=os.getenv('NETBOX_TOKEN'))

# find vm object
vm = nb.virtualization.virtual_machines.get(name=NAME)
if vm is None:
  fail("no such vm")

# find primary ip object
ip = nb.ipam.ip_addresses.get(vm.primary_ip.id)
if ip is None:
  fail("invalid primary ip")

# construct "virtual" configuration
res = { 'virtual': {} }
res['virtual']['name'] = NAME
res['virtual']['fqdn'] = ip.dns_name
res['virtual']['uuid'] = vm.custom_fields['uuid']
res['virtual']['storage'] = vm.custom_fields['storage']
res['virtual']['cpus'] = vm['vcpus']
res['virtual']['ram'] = vm['memory']
res['virtual']['disk_size'] = vm['disk']
if 'cluster' in vm:
  res['virtual']['cluster'] = vm['cluster']['name']
  cluster_nodes = nb.dcim.devices.filter(cluster_id=vm['cluster']['id'])
  if len(cluster_nodes) == 0:
    fail("cluster without nodes!")
  chosen_node = cluster_nodes[0]
  res['virtual']['host'] = chosen_node['name']

print("# generated from netbox. do not change manually")
print(yaml.dump(res))
