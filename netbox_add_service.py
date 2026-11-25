#!/usr/bin/env python3

from sys import stderr,exit,argv
import argparse,json,os,pynetbox
from ipaddress import ip_interface

# display error & bail out
def fail(*messages):
  print(*messages, file=stderr)
  exit(1)


doc = """ 
Add service to existing device or vm.

## Usage:
%s DEVICE_FQDN SERVICE_FQDN PROTO/PORT [IP]

""" % argv[0]


def main():
  parser = argparse.ArgumentParser(description='Add a service to an existing device or VM.')
  parser.add_argument('host', help='Device or VM name')
  parser.add_argument('service', help='Service name')
  parser.add_argument('protocol_port', help='Protocol and port, e.g. tcp/443')
  parser.add_argument('ip', nargs='?', help='IPv4 or IPv6 address assigned to the device or VM, with an optional prefix length')
  parser.add_argument('-n', '--dry-run', action='store_true', help='Show planned changes without saving')
  args = parser.parse_intermixed_args()
  FQDN = args.host
  SERVICE = args.service
  try:
    PROTO, PORT = args.protocol_port.split('/')
    PORT = int(PORT)
  except ValueError:
    parser.error('expected protocol/port, e.g. tcp/443')
  PROTO = PROTO.lower()
  if args.ip is not None:
    try:
      requested_ip = ip_interface(args.ip)
    except ValueError:
      parser.error('ip must be an IPv4 or IPv6 address, optionally with a prefix length')


  print(FQDN, SERVICE, PROTO, PORT)

  if PORT not in range(1,65535):
    fail("invalid port number")
  if PROTO not in ['tcp','udp']:
    fail("invalid proto - use TCP or UDP")
  
  nb = pynetbox.api(os.getenv('NETBOX_API_URL'), token=os.getenv('NETBOX_TOKEN'))

  # find device or vm
  vm = nb.virtualization.virtual_machines.get(name=FQDN)
  dev = nb.dcim.devices.get(name=FQDN)

  # make sure it exists
  if vm is None and dev is None:
      fail("no such vm or device")
  if vm is not None and dev is not None:
      fail("both a vm and a device have this name; service parent is ambiguous")

  if vm is not None:
    parent = vm
    parent_type = 'virtualization.virtualmachine'
  else:
    parent = dev
    parent_type = 'dcim.device'

  # make sure the service does not already exists
  test_services = nb.ipam.services.filter(name=SERVICE, protocol=PROTO, port=PORT)
  if len(test_services) > 0:
      fail("service already exists")

  # make sure if similary named service exists, it is on same device or vm
  for service in nb.ipam.services.filter(name=SERVICE):
    if (service.parent_object_type != parent_type or
        service.parent_object_id != parent.id):
      fail("services with requested name must reside on %s '%s'" % (
        service.parent_object_type, service.parent,
      ))

  req = {
          'name': SERVICE,
          'protocol': PROTO,
          'ports': [PORT],
          'parent_object_type': parent_type,
          'parent_object_id': parent.id,
          }

  if args.ip is not None:
    owner_field = 'virtual_machine' if vm is not None else 'device'
    matches = []
    for ip in nb.ipam.ip_addresses.filter(**{f'{owner_field}_id': parent.id}):
      assigned_ip = ip_interface(ip.address)
      if assigned_ip.ip != requested_ip.ip:
        continue
      if '/' in args.ip and assigned_ip != requested_ip:
        continue
      # NetBox's device filter can also return other virtual chassis members' IPs.
      owner = getattr(ip.assigned_object, owner_field, None)
      if owner is not None and owner.id == parent.id:
        matches.append(ip.id)
    if not matches:
      fail(f"IP address {args.ip} is not assigned to {FQDN}")
    if len(matches) > 1:
      fail(f"IP address {args.ip} matches multiple addresses on {FQDN}")
    req['ipaddresses'] = matches

  if args.dry_run:
    print('Would create service (dry run): ' + json.dumps(req, ensure_ascii=False, sort_keys=True))
    return
  nb.ipam.services.create(req)
 
if __name__ == "__main__":
  main()
