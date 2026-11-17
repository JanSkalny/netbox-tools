#!/usr/bin/env python3

from sys import stderr,exit,argv
import argparse,json,os,pynetbox

# display error & bail out
def fail(*messages):
  print(*messages, file=stderr)
  exit(1)


doc = """ 
Add service to existing device or vm.

## Usage:
%s DEVICE_FQDN SERVICE_FQDN PROTO/PORT

""" % argv[0]


def main():
  parser = argparse.ArgumentParser(description='Add a service to an existing device or VM.')
  parser.add_argument('host', help='Device or VM name')
  parser.add_argument('service', help='Service name')
  parser.add_argument('protocol_port', help='Protocol and port, e.g. tcp/443')
  parser.add_argument('-n', '--dry-run', action='store_true', help='Show planned changes without saving')
  args = parser.parse_args()
  FQDN = args.host
  SERVICE = args.service
  try:
    PROTO, PORT = args.protocol_port.split('/')
    PORT = int(PORT)
  except ValueError:
    parser.error('expected protocol/port, e.g. tcp/443')
  PROTO = PROTO.lower()


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

  if args.dry_run:
    print('Would create service (dry run): ' + json.dumps(req, ensure_ascii=False, sort_keys=True))
    return
  nb.ipam.services.create(req)
 
if __name__ == "__main__":
  main()
