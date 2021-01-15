#!/usr/bin/env python3

from sys import stderr,exit,argv
import json,yaml,os,ipaddress,random,pynetbox
import requests as req
from pprint import pprint
from uuid import uuid4

# display error & bail out
def fail(*messages):
  print(*messages, file=stderr)
  exit(1)

def generate_mac():
  prefix = [0x52, 0x54, 0x00] 
  suffix = [random.randint(0,0xFF) for _ in range(3)]
  return ':'.join(map(lambda x: "%02x" % x, [*prefix, *suffix] ))


doc = """ 
Add interface to existing device or vm.

## Usage:
%s FQDN IFACE_NAME (VLAN) (IP+n) (MAC)

""" % argv[0]


def main():
  # parse inputs
  if len(argv) < 3:
      fail("error, invalid number of args!\n%s" % doc) 

  VLAN = None
  ADDR = None
  MAC = None

  FQDN = argv[1]
  IFACE = argv[2] 
  if len(argv) >= 4:
      VLAN = int(argv[3])
  if len(argv) >= 5:
      ADDR = int(argv[4]) 
  if len(argv) >= 6:
      MAC = argv[5]
  
  nb = pynetbox.api(os.getenv('NETBOX_API_URL'), token=os.getenv('NETBOX_TOKEN'))

  # find device or vm
  vm = nb.virtualization.virtual_machines.get(name=FQDN)
  dev = nb.dcim.devices.get(name=FQDN)

  # make sure it exists
  if vm == None and dev == None:
      fail("no such vm or device")

  # make sure it does not have this interface already
  if vm != None:
    test_iface = nb.virtualization.interfaces.get(virtual_machine=FQDN, name=IFACE)
  if dev != None:
    test_iface = nb.dcim.interfaces.get(device=FQDN, name=IFACE)
  if test_iface != None:
    fail("interface already exists")

  vlan = None
  # validate VLAN 
  if VLAN != None:
    vlan = nb.ipam.vlans.get(vid=VLAN)

    # TODO:
    # if this is a vm, make sure vlan is already allocated to a cluster


  # validate ip no and segment
  iface_addr_masked = None
  net = None
  if ADDR != None:
    net = nb.ipam.prefixes.get(vlan_vid=VLAN)
    
    # make sure this address belongs to the network
    net_addr = ipaddress.ip_network(net.prefix)
    if net_addr.num_addresses - 2 < ADDR:
        fail("network segment is too small")
    if ADDR <= 0:
        fail("can't assign network address")
    iface_addr = net_addr[ADDR]
    iface_addr_masked = "%s/%d" % (iface_addr, net_addr.prefixlen)

    # make sure this address is free
    test_addr = nb.ipam.ip_addresses.get(address=iface_addr)
    if test_addr != None:
        fail("address already assigned")

  # TODO: make sure mac address is globally unique!!!
  if MAC == None:
      MAC = generate_mac()

  iface_data = {
          'name': IFACE,
          'type': "virtual",
          'mode': "access",
  }

  if not IFACE.startswith('br'):
    iface_data['mac_address'] = MAC
  if vlan != None:
    iface_data['untagged_vlan'] = vlan.id
    iface_data['description'] = vlan.name

  # create interface object
  if vm != None:
    iface_data['virtual_machine'] = vm.id
    iface = nb.virtualization.interfaces.create(iface_data)
  if dev != None:
    iface_data['device'] = dev.id
    iface = nb.dcim.interfaces.create(iface_data)

  # create ip address and assign to interface
  if iface_addr_masked != None:
    ip_data = {
            'address': iface_addr_masked,
            'family': 4,
            'interface': iface.id,
            'dns_name': FQDN,
            }
    ip = nb.ipam.ip_addresses.create(ip_data)

 
if __name__ == "__main__":
  main()
