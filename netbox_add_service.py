#!/usr/bin/env python3

from sys import stderr,exit,argv
import json,yaml,os,ipaddress,random,pynetbox
import requests as req
from pprint import pprint
from uuid import uuid4

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
  if vm == None and dev == None:
      fail("no such vm or device")

  # make sure the service does not already exists
  test_services = nb.ipam.services.filter(name=SERVICE, protocol=PROTO, port=PORT)
  if len(test_services) > 0:
      fail("service already exists")

  # make sure if similary named service exists, it is on same device or vm
  test_services = nb.ipam.services.filter(name=SERVICE)
  if len(test_services) > 0:
    if test_services[0].virtual_machine:
      if vm == None or test_services[0].virtual_machine.id != vm.id:
        fail("services with requested name must reside on vm '%s'" % test_services[0].virtual_machine.name)
    elif test_services[0].device:
      if dev == None or test_services[0].device.id != dev.id:
        fail("service(s) with requested name must reside on device '%s'" % test_services[0].device.name)
    else:
      pprint(dict(test_services[0]))
      fail("wut wut!")

  req = {
          'name': SERVICE,
          'protocol': PROTO,
          'port': PORT,
          }
  if vm != None:
    req['virtual_machine'] = vm.id
  if dev != None:
    req['device'] = dev.id

  nb.ipam.services.create(req)
 
if __name__ == "__main__":
  main()
