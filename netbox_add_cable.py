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

def generate_mac():
  prefix = [0x52, 0x54, 0x00]
  suffix = [random.randint(0,0xFF) for _ in range(3)]
  return ':'.join(map(lambda x: "%02x" % x, [*prefix, *suffix] ))


def main():

  parser = argparse.ArgumentParser()
  parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  parser.add_argument('-t', '--tenant', help='Tenant name (defaults to NETBOX_DEFAULT_TENANT env)', default=os.getenv('NETBOX_DEFAULT_TENANT'))
  parser.add_argument('-a', '--host-a', help='Device or VM name', required=True)
  parser.add_argument('-0', '--port-a', help='Interface name', required=True)
  parser.add_argument('-b', '--host-b', help='Device or VM name', required=True)
  parser.add_argument('-1', '--port-b', help='Interface name', required=True)
  parser.add_argument('-y', '--type', help='Cable type')
  parser.add_argument('-d', '--description', help='Interface description.')
  parser.add_argument('-l', '--label', help='Physical interface label (invalid for virtual interfaces)')
  parser.add_argument('-c', '--color', help='Cable color')
  parser.add_argument('-L', '--length', help='Cable length')
  parser.add_argument('-U', '--units', help='Cable length units', default='cm')

  args = parser.parse_args()

  # connect to netbox
  nb = pynetbox.api(args.api_url, args.token)

  # find device or vm
  vm_a = nb.virtualization.virtual_machines.get(name=args.host_a)
  dev_a = nb.dcim.devices.get(name=args.host_a)

  # make sure device or vm exists
  if vm_a == None and dev_a == None:
    fail("no such vm or device")
  assert not (vm_a != None and dev_a != None)

  # find device or vm
  vm_b = nb.virtualization.virtual_machines.get(name=args.host_b)
  dev_b = nb.dcim.devices.get(name=args.host_b)

  # make sure device or vm exists
  if vm_b == None and dev_b == None:
    fail("no such vm or device")
  assert not (vm_b != None and dev_b != None)

  # find interface a
  if vm_a != None:
    if_a = nb.virtualization.interfaces.get(virtual_machine=args.host_a, name=args.port_a)
    obj_a = vm_a
  if dev_a != None:
    if_a = nb.dcim.interfaces.get(device=args.host_a, name=args.port_a)
    obj_a = dev_a
  if if_a == None:
    fail("non-existing inteface A")

  # find interface a
  if vm_b != None:
    if_b = nb.virtualization.interfaces.get(virtual_machine=args.host_b, name=args.port_b)
    obj_b = vm_b
  if dev_b != None:
    if_b = nb.dcim.interfaces.get(device=args.host_b, name=args.port_b)
    obj_b = dev_b
  if if_b == None:
    fail("non-existing inteface B")

  # no units if no length is specified
  if not args.length:
    args.units = None

  # determine vm/dev and port types
  #termination_a_type = f"{obj_a.endpoint.name}.{if_a.endpoint.name}"
  #termination_b_type = f"{obj_b.endpoint.name}.{if_b.endpoint.name}"

  termination_a_type = '.'.join(if_a.endpoint.url.split('/')[-2:])[:-1]
  termination_b_type = '.'.join(if_b.endpoint.url.split('/')[-2:])[:-1]

  cable_data = { 
                'a_terminations': [ {
                    'object_id': if_a.id,
                    'object_type': termination_a_type
                    } ],
                'b_terminations': [ {
                    'object_id': if_b.id,
                    'object_type': termination_b_type
                    } ],
  }

  # optional arguments
  if args.description != None:
    cable_data['description'] = args.description
  if args.type != None:
    cable_data['type'] = args.type
  if args.label != None:
    cable_data['label'] = args.label
  if args.color != None:
    cable_data['color'] = args.color
  if args.length != None:
    cable_data['length'] = args.length
  if args.units != None:
    cable_data['length_unit'] = args.units

  cable = nb.dcim.cables.create(cable_data)
  print(cable)


if __name__ == "__main__":
  main()
