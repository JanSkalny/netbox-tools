#!/usr/bin/env python3

from sys import stderr,exit,argv
import os,pynetbox,time
from pprint import pprint
from itertools import chain

# display error & bail out
def fail(*messages):
  print(*messages, file=stderr)
  exit(1)

# display warning but continue
def warn(*messages):
  print(*messages, file=stderr)



doc = """
Generate NS zone file from netbox IPs, VMs, devices and service names.

## Usage:
%s ZONE

""" % argv[0]


def get_forward_records(nb, ZONE):
  records = {}

  # find everything related to this DNS zone
  vms = nb.virtualization.virtual_machines.filter("."+ZONE)
  devices = nb.dcim.devices.filter("."+ZONE)
  services = nb.ipam.services.filter("."+ZONE)
  ips = nb.ipam.ip_addresses.filter("."+ZONE)

  # vms and devices first
  for x in chain(vms,devices):
    name = x.name.replace("."+ZONE,"")
    if x.primary_ip4 == None:
      warn("found entry without primary ip address", x.name)
    else:
      records[name] = x.primary_ip4.address.split('/')[0]

  for x in services:
    name = x.name.replace("."+ZONE,"")
    ip = None
    if x.virtual_machine:
      vm = nb.virtualization.virtual_machines.get(x.virtual_machine.id)
      if vm.primary_ip4 == None:
        warn("found service with vm without primary ip address", x.virtual_machine.name)
      else:
        ip = vm.primary_ip4.address.split('/')[0]
    if x.device:
      dev = nb.dcim.devices.get(x.device.id)
      if dev.primary_ip4 == None:
        warn("found service with device without primary ip address", x.device.name)
      else:
        ip = dev.primary_ip4.address.split('/')[0]
    if ip == None:
      warn("service without ip address!", x.name)
    if name in records and records[name] != ip:
      warn("service name conflit with different address", name, records[name], "using service address", ip)
      # service name has priority
      records[name] = ip
    else:
      records[name] = ip

  # names not used by any services or vms or devices
  for x in ips:
    if x.vrf:
      continue
    name = x.dns_name.replace("."+ZONE,"")
    if name == '':
      warn('empty name detected', x)
      continue
    if name not in records:
      records[name] = x.address.split('/')[0]
    #else:
    #  warn("ignored ipam record", x.dns_name, x.address)

  return records


def get_reverse_records(nb, ZONE):
  records = {}

  ip = '.'.join(reversed(ZONE.replace('.in-addr.arpa','').split('.')))

  ips = nb.ipam.ip_addresses.filter(ip+".")

  for ip in ips:
    if '.' in ip.dns_name:
      records[ip.dns_name] = int(ip.address.split('/')[0].split('.')[-1])

  return records


def main():
  # parse inputs
  if len(argv) < 2:
    fail("error, invalid number of args!\n%s" % doc)

  ZONE = argv[1]
  nb = pynetbox.api(os.getenv('NETBOX_API_URL'), token=os.getenv('NETBOX_TOKEN'))

  records = {}

  if ZONE.endswith('.in-addr.arpa'):
    records = get_reverse_records(nb, ZONE)
    zone_template = """
$ORIGIN {origin}.
$TTL 86400

@ IN SOA ns.{zone}. admin.{zone}. (
 {serial} ; serial
 900 ; refresh
 900 ; retry
 2419200 ; expire
 120 ; minimum ttl
)

$TTL 120

@ IN NS ns.{zone}.

1 IN PTR . ;
"""

    res = zone_template.format(origin=ZONE, serial=int(time.time()), zone='.'.join(list(records.items())[0][0].split('.')[1:]))
    for host, ip_num in sorted(records.items(), key=lambda x: x[1]):
      res += "%s IN PTR %s. ;\n" % (ip_num, host)

    print(res)
  else:
    records = get_forward_records(nb, ZONE)
    zone_template = """
$ORIGIN {origin}.
$TTL 86400

@ IN SOA ns.{origin}. admin.{origin}. (
 {serial} ; serial
 900 ; refresh (ako casto by sekundar checkoval primar)
 900 ; retry (ak sa refresh nepodaril, ako casto robit retry)
 2419200 ; expire (kolko to sekundar podrzi, kym prestane byt autoritativny)
 120 ; minimum ttl
 )

$TTL 120

@ IN NS ns.{origin}.

"""

    res = zone_template.format(origin=ZONE, serial=int(time.time()))
    for host, ip in sorted(records.items()):
      if ip:
        res += "%s IN A %s\n" % (host, ip)

    print(res)

if __name__ == "__main__":
  main()
