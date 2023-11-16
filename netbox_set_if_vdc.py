#!/usr/bin/env python3

from sys import stderr,exit,argv
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
  parser.add_argument('-V', '--vdc', help='VDC name for givet interface (ie. "root"). Defaults to None = unset VDC.', default=None)

  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, args.token)

  # find device
  dev = nb.dcim.devices.get(name=args.host)
  if not dev:
    fail("no such device")

  # find interface
  if dev != None:
    ifaces = nb.dcim.interfaces.filter(device=args.host, name=args.iface)
  if len(ifaces) == 0:
    fail("interface does not exist")

  # list all device vdcs
  valid_vdcs = nb.dcim.virtual_device_contexts.all()
  vdcs_map = {}
  for vdc in valid_vdcs:
    vdcs_map[vdc.name] = vdc.id

  # find vdc
  for iface in ifaces:
    iface_vdcs = []
    for vdc in iface.vdcs:
      iface_vdcs.append(vdc.name)
    
    if args.vdc == None:
      if len(iface_vdcs) > 0:
        iface.vdcs = []
        iface.save()
        print("remove all vdcs from interface", iface)
    else:
      if args.vdc not in iface_vdcs:
        iface.vdcs.append(vdcs_map[args.vdc])
        iface.save()
        print("add vdc",args.vdc,"from interface", iface)


if __name__ == "__main__":
  main()
