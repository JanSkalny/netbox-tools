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
  parser.add_argument('-s', '--site', help='Site name (defaults to NETBOX_DEFAULT_SITE evn)', default=os.getenv('NETBOX_DEFAULT_SITE'))
  parser.add_argument('-H', '--host', help='Device or VM name', required=True)
  parser.add_argument('-i', '--iface', help='Interface name', required=True)
  parser.add_argument('-a', '--add', help='Add VLANs to existing ones instead of replacing them. (defaults to false)', action='store_true')
  parser.add_argument('-x', '--mark-as-tagged', help='Override interface mode to tagged. (defaults to false)', action='store_true')
  parser.add_argument('-V', '--vlans', help='VLAN list in Cisco compatible notation. eg. 1-9,20,30-39', required=True)
  parser.add_argument('-n', '--no-change', help='Don\'t change anything in netbox, just show what would be done', action='store_true')

  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, args.token)

  # find device or vm
  dev = nb.dcim.devices.get(name=args.host)
  vm = nb.virtualization.virtual_machines.get(name=args.host)

  # make sure device or vm exists
  if vm == None and dev == None:
    fail("no such vm or device")
  assert not (vm != None and dev != None)

  # find interface
  if vm != None:
    ifaces = nb.virtualization.interfaces.filter(virtual_machine=args.host, name=args.iface)
  if dev != None:
    ifaces = nb.dcim.interfaces.filter(device=args.host, name=args.iface)
  if len(ifaces) == 0:
    fail("interface does not exist")

  # parse vlan list
  vlan_ranges = args.vlans.split(',')
  requested_vids = set()
  for vlan_range in vlan_ranges:
    lo_hi = vlan_range.split('-')
    if len(lo_hi) > 1:
      requested_vids.update(range(int(lo_hi[0]), int(lo_hi[1])+1))
    else:
      requested_vids.add(int(lo_hi[0]))

  # get all vlans from the site
  site_vlans = nb.ipam.vlans.filter() #site=args.site)

  site_vids = []
  found_vids = set()
  requested_ids = set()
  for site_vlan in site_vlans:
    for vid in requested_vids:
      if vid == site_vlan.vid:
        found_vids.add(vid)
        requested_ids.add(site_vlan.id)

  missing_vids = requested_vids.difference(found_vids)
  if len(missing_vids) != 0:
    fail("requested non-existing vlans", missing_vids)

  for iface in ifaces:
    iface_vids = set()
    iface_ids = set()
    for iface_vlan in iface.tagged_vlans:
      iface_vids.add(iface_vlan.vid)
      iface_ids.add(iface_vlan.id)

    if args.add:
      requested_ids.update(iface_ids)
      requested_vids.update(iface_vids)

    #print('found',found_vids)
    #print('requested',requested_vids)
    #print('existing',iface_vids)

    # check if we need to do something
    if iface_vids != requested_vids:
      # and if interface is in tagged mode
      if not iface.mode or iface.mode.value != 'tagged':
        if args.mark_as_tagged:
          iface.mode = 'tagged'
        else:
          fail('interface not in tagged mode', args.host, iface.name, iface.mode)

      iface.tagged_vlans = list(requested_ids)

      removed_vids = set(iface_vids).difference(set(requested_vids))
      added_vids = set(requested_vids).difference(set(iface_vids))

      if not args.no_change:
        if added_vids:
          print(args.host, iface.name, "added vlans:", added_vids)
        if removed_vids:
          print(args.host, iface.name, "removed vlans:", removed_vids)
        iface.save()
      else:
        if added_vids:
          print(args.host, iface.name, "will add vlans:", added_vids)
        if removed_vids:
          print(args.host, iface.name, "will remove vlans:", removed_vids)
      #print('vlans before', list(iface_vids))
      #print('vlans after', list(requested_vids))
    else:
      print(args.host, iface.name, 'no change')

if __name__ == "__main__":
  main()
