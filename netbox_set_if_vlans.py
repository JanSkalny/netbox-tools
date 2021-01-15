#!/usr/bin/env python3

from sys import stderr,exit,argv
import os,pynetbox
from pprint import pprint

doc = """ 
Set only specified VLANs on device interface.

## Usage:
%s site-name dev-name iface-name vlans 

`vlans` must be in cisco format. (eg. "1,2,5-10")

""" % argv[0]

# display error & bail out
def fail(*messages):
  print(*messages, file=stderr)
  exit(1)

def main():
  # parse inputs
  if len(argv) != 5:
      fail("error, invalid number of args!\n%s" % doc) 

  SITE = argv[1]
  FQDN = argv[2]
  IFACE = argv[3] 
  VLAN_LIST = argv[4] 
  
  nb = pynetbox.api(os.getenv('NETBOX_API_URL'), token=os.getenv('NETBOX_TOKEN'))

  # find device 
  dev = nb.dcim.devices.get(name=FQDN, site=SITE)
  if dev == None:
      fail("no such vm or device")

  # find interface
  iface = nb.dcim.interfaces.get(device=FQDN, name=IFACE)
  if iface == None:
    fail("interface does not exist")

  # parse vlan list
  vlan_ranges = VLAN_LIST.split(',')
  requested_vlans = []
  for vlan_range in vlan_ranges:
    lo_hi = vlan_range.split('-')
    if len(lo_hi) > 1:
      requested_vlans += range(int(lo_hi[0]), int(lo_hi[1]))
    else:
      requested_vlans.append(int(lo_hi[0]))

  # get all vlans from the site
  site_vlans = nb.ipam.vlans.filter(site=SITE)

  # validate VLAN 
  valid_vlans = []
  for site_vlan in site_vlans:
    if site_vlan.vid in requested_vlans:
      valid_vlans.append(site_vlan)

  #pprint(dict(iface))
  pprint(valid_vlans)

  # make sure interface is in "trunk" mode 
  # add vlans and save changes
  iface.mode = 'tagged'
  iface.tagged_vlans = valid_vlans
  iface.save()

  #XXX: if interface is "lag", update also all children
  #lag_children = nb.dcim.interfaces.filter(device=FQDN, lag_id=iface.id)
  #for lag_child in lag_children:
  #  lag_child.mode = 'tagged'
  #  lag_child.tagged_vlans = valid_vlans
  #  lag_child.save()

if __name__ == "__main__":
  main()
