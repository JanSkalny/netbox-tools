#!/usr/bin/env python3

from sys import argv,stderr,exit
import json, os, yaml, pynetbox, re, ipaddress
from collections import defaultdict
from pprint import pprint

doc = """ 
Generate networking configuration for device or VM.

## Usage
%s "FQDN" 

""" % (argv[0])

def assume_ip_gateway(network):
  return str(ipaddress.ip_network(network,False)[1]).split('/')[0]

def debug(*msg):
  return
  print(*msg, file=stderr)

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
  fail("make up your mind. duplicit naming detected!")

ifaces = None
primary_addr = None
config_context = None

# get all interfaces, config_context and primary address
if vm:
  ifaces = nb.virtualization.interfaces.filter(virtual_machine=FQDN)
  config_context = vm['config_context']
  primary_addr = vm['primary_ip']['address']
if dev:
  ifaces = nb.dcim.interfaces.filter(device=FQDN)
  config_context = dev['config_context']
  primary_addr = dev['primary_ip']['address']

res = { 'networking': {} }
if config_context and 'networking' in config_context:
  res['networking'] = config_context.networking

lag_ifaces = defaultdict(list)
blacklist = [] 

# make sure all non-oob mgmt ifaces are in output
for iface in ifaces:
  if dev and iface.mgmt_only:
    continue
  if iface.name not in res['networking']:
    res['networking'][iface.name] = {}

# find all lag parent and children interfaces
if dev:
  for iface in ifaces:
    if not iface.lag:
      continue
    lag_ifaces[iface.lag.name].append(iface.name)
    debug("blacklist.append", iface.name)
    blacklist.append(iface.name)
  for lag_parent, lag_children in lag_ifaces.items():
    res['networking'][lag_parent]['bond_slaves'] = lag_children
    for lag_child in lag_children:
      res['networking'][lag_child]['bond_master'] = lag_parent

for iface in ifaces: 
  # ignore management interfaces
  if dev and iface.mgmt_only:
    continue

  # mac address of interface
  if iface.mac_address:
    res['networking'][iface.name]['ether'] = iface.mac_address.lower()

  # if we encounter tagged LACP interface, assume device is hypervisor or cluster node.
  # create vlan interfaces and associated bridge interfaces.
  if iface.mode and iface.mode.value == 'tagged' and not iface.lag:
    for vlan in iface.tagged_vlans:
      if 'vlan%d' % vlan.vid not in res['networking']:
        res['networking']['vlan%d' % vlan.vid] = {}
      res['networking']['vlan%d' % vlan.vid]['vlan-iface'] = iface.name 
      res['networking']['vlan%d' % vlan.vid]['vlan-id'] = vlan.vid

      if 'brVlan%d' % vlan.vid not in res['networking']:
        res['networking']['brVlan%d' % vlan.vid] = {}
      res['networking']['brVlan%d' % vlan.vid]['bridge_ports'] = 'vlan%d' % vlan.vid
 
  # rest is for non-lag interfaces
  if iface.name in blacklist:
    debug("blacklist iface", iface.name)
    continue

  # lookup ip address, if interface has one
  ip = None
  if dev:
    ip = nb.ipam.ip_addresses.get(interface_id=iface.id)
  if vm:
    ip = nb.ipam.ip_addresses.get(vminterface_id=iface.id)
  if ip:
    res['networking'][iface.name]['address'] = ip.address
    #XXX: since there is not "gateway" role function, guess default gateway 
    # for interface with primary address, if not defined already
    if 'gateway' in res['networking'][iface.name]:
      warn(iface.name, "already has gateway defined")
    elif ip.address == primary_addr:
      gateway_addr = assume_ip_gateway(ip.address)
      res['networking'][iface.name]['gateway'] = gateway_addr

  # for vm, generate matching 'virtual_host_iface'
  if vm:
    res['networking'][iface.name]['virtual_host_iface'] = 'brVlan%d' % iface.untagged_vlan.vid

# output
print("# generated from netbox. do not change manually")
print(yaml.dump(res))
