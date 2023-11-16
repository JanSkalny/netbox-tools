#!/usr/bin/env python3

from sys import stderr,exit,argv
import os,pynetbox,argparse,yaml

# display error & bail out
def fail(*messages):
  print(*messages, file=stderr)
  exit(1)

# display warning message
def warn(*messages):
  print(*messages, file=stderr)

def assume_ip_gateway(network):
  return str(ipaddress.ip_network(network)[1]).split('/')[0]


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-T', '--token', help='Netbox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='Netbox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  parser.add_argument('-t', '--tenant', help='Tenant name (defaults to NETBOX_DEFAULT_TENANT env)', default=os.getenv('NETBOX_DEFAULT_TENANT'))
  parser.add_argument('-s', '--site', help='Site name (defaults to NETBOX_DEFAULT_SITE evn)', default=os.getenv('NETBOX_DEFAULT_SITE'))
  parser.add_argument('-H', '--host', help='Firewall name', required=True)
  args = parser.parse_args()

  # connect to netbox
  nb = pynetbox.api(args.api_url, args.token)
  
  dev = nb.dcim.devices.get(name=args.host)
  if not dev:
    fail('no such device')

  # build a list of vlans and assigned trunk ports
  vlan_map = {}
  ifaces = nb.dcim.interfaces.filter(device=args.host,type='virtual')

  res = []
  for iface in ifaces:
    if not iface.mode:
      warn('interface',iface,'without mode')
      continue
    #print(dict(iface))
    if iface.mode.value == 'access':
      ip = nb.ipam.ip_addresses.get(interface_id=iface.id)
      if not ip:
        warn('interface without ip', iface)
        continue
      if not iface.untagged_vlan:
        warn('access interface without vlan', iface)
        continue
      if len(iface.vdcs) == 0:
        warn('interface without vdom', iface)
        continue
      vdom = iface.vdcs[0].name
      role = 'lan'
      for t in iface.tags:
        if t.slug == 'wan':
          role = 'wan'
      res.append({
              'name': iface.name,
              'description': iface.description,
              'parent': iface.parent.name,
              'address': ip.address,
              'vlan': iface.untagged_vlan.vid,
              'role': role,
              'vdom': vdom,
              })

  print(yaml.dump({'forti_interfaces':res}))

if __name__ == "__main__":
  main()
