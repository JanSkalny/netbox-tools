#!/usr/bin/env python3

from sys import stderr,exit,argv
import os,pynetbox

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
  # parse inputs
  if len(argv) < 4:
      fail("error, invalid number of args!\n%s" % doc) 

  FQDN = argv[1]
  SERVICE = argv[2] 
  PROTO,PORT = argv[3].split('/')
  PORT = int(PORT)
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

  nb.ipam.services.create(req)
 
if __name__ == "__main__":
  main()
