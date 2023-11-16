#!/usr/bin/env python3

from sys import stderr,exit,argv
import json,yaml,os,ipaddress,random,pynetbox,argparse
import requests as req
from pprint import pprint
from uuid import uuid4

# display error & bail out
def fail(*messages):
  print(*messages, file=stderr)
  exit(1)

def warn(*messages):
  print(*messages, file=stderr)

def generate_mac():
  prefix = [0x52, 0x54, 0x00]
  suffix = [random.randint(0,0xFF) for _ in range(3)]
  return ':'.join(map(lambda x: "%02x" % x, [*prefix, *suffix] ))


def main():

  parser = argparse.ArgumentParser()
  parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  parser.add_argument('-t', '--tenant', help='Tenant name (defaults to NETBOX_DEFAULT_TENANT env)', default=os.getenv('NETBOX_DEFAULT_TENANT'))
  parser.add_argument('-H', '--host', help='Device or VM name', required=True)
  parser.add_argument('-v', '--vlan', nargs="+", help='Interface VLAN(s)', type=int)
  parser.add_argument('-a', '--address', help='Usable IP address within given VLAN, provide the N-th address (net address + number)', type=int)
  parser.add_argument('-i', '--iface', help='Interface name', required=True)
  parser.add_argument('-m', '--mac', help='Interface MAC address (xx:xx:xx:xx:xx:xx format)')
  parser.add_argument('-o', '--mode', help='Interface mode (eg. tagged, tagged-all, access. defaults to access if one vlan is specified, or tagged if more')
  parser.add_argument('-M', '--mtu', help='Interface MTU (in bytes, default is unspecified)', type=int)
  parser.add_argument('-y', '--type', help='Interface type (defaults to virtual)', default='virtual')
  parser.add_argument('-b', '--bond', nargs="+", help='LACP slave interface(s)')
  parser.add_argument('-x', '--management-only', help='Mark interface as management-only interface (oob)', action='store_true')
  parser.add_argument('-p', '--primary', help='Mark address as primary address for device/vm', action='store_true')
  parser.add_argument('-d', '--description', help='Interface description. (default for access mode is access vlans name)')
  parser.add_argument('-l', '--label', help='Physical interface label (invalid for virtual interfaces)')
  parser.add_argument('-f', '--fqdn', help='FQDN for IP address')
  parser.add_argument('-P', '--parent', help='Set parent interface')
  parser.add_argument('-n', '--net', help='Manualy select preffix (for interfaces without VLANs, eg. tunnels)', default=None)

  args = parser.parse_args()

  # connect to netbox
  nb = pynetbox.api(args.api_url, args.token)

  # find device or vm
  vm = nb.virtualization.virtual_machines.get(name=args.host)
  dev = nb.dcim.devices.get(name=args.host)

  # make sure device or vm exists
  if vm == None and dev == None:
    fail("no such vm or device")
  assert not (vm != None and dev != None)

  # if one vlan is specified, mode defaults to access
  if args.vlan and len(args.vlan) == 1 and args.mode == None:
    args.mode = 'access'

  # if more than one vlan is specified, mode defaults to tagged
  if args.vlan and len(args.vlan) > 1 and args.mode == None:
    args.mode = 'tagged'

  # access interface must have exactly one vlan
  if args.mode == 'access' and (len(args.vlan) > 1 or args.vlan == None):
    fail("access mode requires exactly one vlan")

  # if bond interface is specified, lag mode is required
  if args.type != 'lag' and args.bond != None:
    fail("lag interface type is required if lacp interfaces are specified")

  # validate parent interface, if any
  parent_iface = None
  if args.parent and args.parent != None:
    if vm != None:
      parent_ifaces = nb.virtualization.interfaces.filter(virtual_machine=args.host, name=args.parent)
    if dev != None:
      parent_ifaces = nb.dcim.interfaces.filter(device=args.host, name=args.parent)
    if parent_ifaces == None or len(parent_ifaces) == 0:
      fail("non-existing parent interface specified", parent)
    if len(parent_ifaces) > 1:
      warn('duplicit parent interfaces found. using first iterface')
    parent_iface = list(parent_ifaces)[0]

  # validate all lacp interfaces
  bond_ifaces = []
  if args.type == 'lag' and args.bond != None:
    for bond in args.bond:
      bond_iface = None
      if vm != None:
        bond_iface = nb.virtualization.interfaces.get(virtual_machine=args.host, name=bond)
      if dev != None:
        bond_iface = nb.dcim.interfaces.get(device=args.host, name=bond)
      if bond_iface == None:
        fail("non-existing bond interface specified", bond)
      bond_ifaces.append(bond_iface)

  # make sure it does not have this interface already
  if vm != None:
    test_iface = nb.virtualization.interfaces.get(virtual_machine=args.host, name=args.iface)
  if dev != None:
    test_iface = nb.dcim.interfaces.get(device=args.host, name=args.iface)
  if test_iface != None:
    fail("interface already exists")

  # TODO:
  # if this is a vm, make sure vlan is already allocated to a cluster

  # validate ip no and segment
  iface_addr_masked = None
  net = None
  if args.address != None:
    # use static prefix selection
    if not args.vlan or len(args.vlan) == 0:
      if not args.net:
        fail('address assignment available only with vlan or net arguments')
      net = list(nb.ipam.prefixes.filter(args.net))[-1]
    else:
      net = nb.ipam.prefixes.filter(vlan_vid=args.vlan)
      if len(net) == 0:
        fail('net not found')
      if len(net) > 1:
        fail('too many networks matching vlan', args.vlan)
      net = list(net)[0]
    if not net:
      fail('net not found')

    # make sure this address belongs to the network
    net_addr = ipaddress.ip_network(net.prefix)
    if net_addr.num_addresses - 2 < args.address:
        fail("network segment is too small")
    if args.address <= 0:
        fail("can't assign network address")
    iface_addr = net_addr[args.address]
    iface_addr_masked = "%s/%d" % (iface_addr, net_addr.prefixlen)

    # make sure this address is free
    test_addr = nb.ipam.ip_addresses.get(address=iface_addr)
    if test_addr != None:
        fail("address already assigned")

  # generate only for virtual machine interface
  if args.mac == None and vm != None:
    args.mac = generate_mac()

  iface_data = {
          'name': args.iface,
          'type': args.type,
          'mode': args.mode,
  }

  # optional arguments
  if args.mac != None:
    iface_data['mac_address'] = args.mac
  if args.mtu != None:
    iface_data['mtu'] = args.mtu
  if args.management_only != None:
    iface_data['mgmt_only'] = args.management_only
  if args.description != None:
    iface_data['description'] = args.description
  if args.label != None:
    iface_data['label'] = args.label
  if parent_iface != None:
    iface_data['parent'] = parent_iface.id

  # access mode interface
  if args.mode == 'access':
    # lookup and assign access vlan
    vid = args.vlan[0]
    vlan = nb.ipam.vlans.get(vid=vid)
    if vlan == None:
      fail("invalid vid specified", vid)
    iface_data['untagged_vlan'] = vlan.id
    # default description for access port
    if args.description != None:
      iface_data['description'] = vlan.name

  # trunk mode interface
  if args.mode != 'access' and args.vlan != None:
    # validate all requested vlans and assign them to turnk
    iface_data['tagged_vlans'] = []
    for vid in args.vlan:
      vlan = nb.ipam.vlans.get(vid=vid)
      if vlan == None:
        fail("invalid vid specified", vid)
      iface_data['tagged_vlans'].append(vlan.id)

  # create interface object
  if vm != None:
    iface_data['virtual_machine'] = vm.id
    iface_type = 'virtualization.vminterface'
    iface = nb.virtualization.interfaces.create(iface_data)
  if dev != None:
    iface_data['device'] = dev.id
    iface_type = 'dcim.interface'
    iface = nb.dcim.interfaces.create(iface_data)

  # create ip address and assign to interface
  if iface_addr_masked != None:
    fqdn = args.host
    if args.fqdn:
      fqdn = args.fqdn
    ip_data = {
            'address': iface_addr_masked,
            'family': 4,
            'assigned_object_type': iface_type,
            'assigned_object_id': iface.id,
            'dns_name': fqdn,
            }
    ip = nb.ipam.ip_addresses.create(ip_data)

    if args.primary:
      if dev:
        dev.primary_ip4 = ip.id
        dev.save()
      if vm:
        vm.primary_ip4 = ip.id
        vm.save()

  # update bonded interfaces to point to this interface
  for bond_iface in bond_ifaces:
    bond_iface.lag = iface.id
    bond_iface.save()


if __name__ == "__main__":
  main()
