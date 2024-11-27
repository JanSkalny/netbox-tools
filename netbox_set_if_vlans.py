#!/usr/bin/env python3

from sys import stderr,exit,argv
import os,pynetbox,argparse

def fail(*messages):
  print(*messages, file=stderr)
  exit(1)

def warn(*messages):
  print(*messages, file=stderr)
  exit(1)


def iface_ensure_mode(iface, mode, override, dry_run=False):
  # check if interface has a mode
  if not iface.mode:
    if not override:
      fail('interface mode not set', iface.name)
    iface.mode = mode
    if dry_run:
      warn('missing interface mode on', iface.name,'will set to', mode)
      return
    iface.save()
    return

  # make sure mode is correct
  if iface.mode.value != mode:
    if override:
      old_mode = iface.mode
      iface.mode = mode
      if not dry_run:
        warn('invalid interface mode on', iface.name, 'will change from', old_mode, 'to', mode)
        iface.save()
      else:
        warn('interface mode on', iface.name, 'changed from', old_mode, 'to', mode)
    else:
      fail('invalid interface mode', iface.name, 'expected mode', mode, 'got', iface.mode)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  parser.add_argument('-t', '--tenant', help='Tenant name (defaults to NETBOX_DEFAULT_TENANT env)', default=os.getenv('NETBOX_DEFAULT_TENANT'))
  parser.add_argument('-s', '--site', help='Site name (defaults to NETBOX_DEFAULT_SITE evn)', default=os.getenv('NETBOX_DEFAULT_SITE'))
  parser.add_argument('-H', '--host', help='Device or VM name', required=True)
  parser.add_argument('-i', '--iface', help='Interface name', required=True)
  parser.add_argument('-a', '--add', help='Add VLANs to existing ones instead of replacing them. (defaults to false)', action='store_true')
  parser.add_argument('-x', '--set-mode', help='Override interface mode to either access or tagged. (defaults to false)', action='store_true')
  parser.add_argument('-V', '--vlans', help='VLAN list in Cisco compatible notation. eg. 1-9,20,30-39')
  parser.add_argument('-v', '--access-vlan', help='Access VLAN number eg. 123')
  parser.add_argument('-n', '--no-change', help='Don\'t change anything in netbox, just show what would be done', action='store_true')

  args = parser.parse_args()

  if not args.vlans and not args.access_vlan:
    fail("either vlans or access-vlan must be specified")

  if args.vlans and args.access_vlan:
    fail("vlans and access-vlan are mutally exclusive")

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

  requested_vids = set()

  # parse trunk vlans
  if args.vlans:
    vlan_ranges = args.vlans.split(',')
    for vlan_range in vlan_ranges:
      lo_hi = vlan_range.split('-')
      if len(lo_hi) > 1:
        requested_vids.update(range(int(lo_hi[0]), int(lo_hi[1])+1))
      else:
        requested_vids.add(int(lo_hi[0]))

  # parse access vlan
  if args.access_vlan:
    requested_vids.add(int(args.access_vlan))

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
    # make sure interface mode is correct
    if args.vlans:
      iface_ensure_mode(iface, 'tagged', args.set_mode, args.no_change)
    if args.access_vlan:
      iface_ensure_mode(iface, 'access', args.set_mode, args.no_change)

    # tagged interface
    if args.vlans:
      iface_vids = set()
      iface_ids = set()

      # update tagged interfaces
      for iface_vlan in iface.tagged_vlans:
        iface_vids.add(iface_vlan.vid)
        iface_ids.add(iface_vlan.id)
      if args.add:
        requested_ids.update(iface_ids)
        requested_vids.update(iface_vids)

      # check if we need to do something
      if iface_vids != requested_vids:
        iface.tagged_vlans = list(requested_ids)
        removed_vids = set(iface_vids).difference(set(requested_vids))
        added_vids = set(requested_vids).difference(set(iface_vids))

        # if we do, and we want to...
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
      else:
        print(args.host, iface.name, 'no change')

    # access interface
    if args.access_vlan:
      access_id = list(requested_ids)[0]
      access_vid = list(requested_vids)[0]
      if iface.untagged_vlan != access_id:
        if args.no_change:
          print(args.host, iface.name, "set access vlan to", access_vid)
        else:
          iface.untagged_vlan = access_id
          iface.save()
      else:
        print(args.host, iface.name, 'no change')


if __name__ == "__main__":
  main()
