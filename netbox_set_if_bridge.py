#!/usr/bin/env python3

from sys import stderr,exit
import os,pynetbox,argparse

def fail(*messages):
  print(*messages, file=stderr)
  exit(1)

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  parser.add_argument('-t', '--tenant', help='Tenant name (defaults to NETBOX_DEFAULT_TENANT env)', default=os.getenv('NETBOX_DEFAULT_TENANT'))
  parser.add_argument('-H', '--host', help='Device or VM name', required=True)
  parser.add_argument('-i', '--iface', help='Interface name', required=True)
  parser.add_argument('-B', '--bridge-iface', '--bridge', help='Parent bridge interface, eg. "br0"', required=True)

  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, args.token)

  # find device or VM
  dev = nb.dcim.devices.get(name=args.host)
  vm = nb.virtualization.virtual_machines.get(name=args.host)
  if dev is None and vm is None:
    fail("no such vm or device")
  if dev is not None and vm is not None:
    fail("both a device and VM match the host name")

  if dev is not None:
    interfaces = nb.dcim.interfaces
    host_filter = {'device_id': dev.id}
  else:
    interfaces = nb.virtualization.interfaces
    host_filter = {'virtual_machine_id': vm.id}

  # find interface
  ifaces = list(interfaces.filter(**host_filter, name=args.iface))
  if len(ifaces) == 0:
    fail("interface does not exist")

  # find bridge interface on the same device or VM
  bridges = list(interfaces.filter(**host_filter, name=args.bridge_iface))
  if len(bridges) == 0:
    fail("bridge interface does not exist")
  if len(bridges) > 1:
    fail("too many bridge interfaces found")

  bridge = bridges[0]
  if any(iface.id == bridge.id for iface in ifaces):
    fail("interface cannot be its own bridge")

  for iface in ifaces:
    if iface.bridge is None or iface.bridge.id != bridge.id:
      print("set bridge for", iface, "->", bridge)
      iface.bridge = bridge.id
      iface.save()

if __name__ == "__main__":
  main()
