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
  parser.add_argument('-i', '--old-name', help='Old interface name', required=True)
  parser.add_argument('-n', '--new-name', help='New interface name', required=True)

  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, args.token)

  # find device
  dev = nb.dcim.devices.get(name=args.host)
  if not dev:
    fail("no such device")

  # find interface
  ifaces = nb.dcim.interfaces.filter(device=args.host, name=args.old_name)
  if len(ifaces) == 0:
    fail("interface does not exist")
  if len(ifaces) > 1:
    fail("too many interfaces found")

  # make sure new name is unique
  test_ifaces = nb.dcim.interfaces.filter(device=args.host, name=args.new_name)
  if len(test_ifaces) != 0:
    fail("target interface already exist")

  # rename interface
  iface = next(ifaces)
  iface.name = args.new_name
  iface.save()


if __name__ == "__main__":
  main()
