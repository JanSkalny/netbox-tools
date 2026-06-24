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


doc = """
Find VM name with specific storage+LUN+cluster.

## Usage:
%s FQDN

""" % argv[0]


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  parser.add_argument('-c', '--cluster', help='Cluster name (defaults to NETBOX_DEFAULT_CLUSTER env)', default=os.getenv('NETBOX_DEFAULT_CLUSTER'))
  parser.add_argument('-S', '--storage', help='Storage device', required=True)
  parser.add_argument('-L', '--lun', help='LUN number', required=True, type=int)
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, args.token)

  # find storage device
  storages = nb.dcim.devices.filter(name=args.storage)
  if len(storages) != 1:
    fail("no such storage device")
  storage = next(storages)

  # find cluster
  if args.cluster:
    cluster = nb.virtualization.clusters.get(name=args.cluster)
    if not cluster:
      fail("no such cluster")

  # find vm with same cluster/storage/lun
  if args.cluster:
    vms = nb.virtualization.virtual_machines.filter(cluster=args.cluster, cf_storage_id=args.lun, cf_storage_device=storage.id)
  else:
    vms = nb.virtualization.virtual_machines.filter(cf_storage_id=args.lun, cf_storage_device=storage.id)

  if len(vms) == 0:
    fail("no such vm")
  if len(vms) > 1:
    fail("too many vms found")

  vm = next(vms)
  print(vm)


if __name__ == "__main__":
  main()
