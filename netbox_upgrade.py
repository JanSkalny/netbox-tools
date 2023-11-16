#!/usr/bin/env python3

from sys import stderr,exit
import json, os, pynetbox, re, datetime, argparse

def debug(*msg):
  return
  print(*msg, file=stderr)

def fail(*msg):
  print(*msg, file=stderr)
  exit(1)

parser = argparse.ArgumentParser()
parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
parser.add_argument('-f', '--upgrade-fw', help='Update last_upgrade_fw field', default=False, action='store_true')
parser.add_argument('-a', '--upgrade-app', help='Update last_upgrade_app field', default=False, action='store_true')
parser.add_argument('-o', '--upgrade-os', help='Update last_upgrade field', default=False, action='store_true')
parser.add_argument('-n', '--no-change', help='Show preview and don\'t modify anything', default=False, action='store_true')
parser.add_argument('fqdn', help='FQDN associated with VM or Device')

args = parser.parse_args()

nb = pynetbox.api(args.api_url, args.token)

dev = None
vm = None

# find vm or device object
vm = nb.virtualization.virtual_machines.get(name=args.fqdn)
dev = nb.dcim.devices.get(name=args.fqdn)

if vm and dev:
  fail("make up your mind. duplicit naming detected!")

x = None
if vm:
  x = vm
if dev:
  x = dev

if x is None:
  fail("no such device or vm")

now = datetime.datetime.now()
d = now.strftime("%Y-%m-%d")


change_fields = []
if args.upgrade_app:
    change_fields.append('last_upgrade_app')
if args.upgrade_fw:
    change_fields.append('last_upgrade_fw')
if args.upgrade_os or not (args.upgrade_app or args.upgrade_fw):
    change_fields.append('last_upgrade')

changed_fields = []
for change_field in change_fields:
    if x.custom_fields[change_field] != d:
        print(f"{change_field}: {x.custom_fields[change_field]} -> {d}")
        x.custom_fields[change_field] = d
        changed_fields.append(change_field)

if len(changed_fields) == 0:
    print("no changes")
else:
    if not args.no_change:
        x.save()
    else:
        print("not saving changes")

