#!/usr/bin/env python3

from sys import stderr,exit,argv
import json,yaml,os,ipaddress,random,pynetbox
import requests as req
from pprint import pprint
from uuid import uuid4

def fail(*messages):
  print(*messages, file=stderr)
  exit(1)

def warn(*messages):
  print(*messages, file=stderr)



nb = pynetbox.api(os.getenv('NETBOX_API_URL'), token=os.getenv('NETBOX_TOKEN'))

# fetch all vms
vms = nb.virtualization.virtual_machines.all()
ids = {}
for vm in vms:

  vm_name = vm['name']
  ip_name = None
  service_name = None

  ip = nb.ipam.ip_addresses.get(id=vm.primary_ip4.id)
  if ip:
    ip_name = ip.dns_name

  services = nb.ipam.services.filter(virtual_machine_id=vm.id, protocol="tcp", port=22)
  if len(services) == 0:
    warn(vm_name, "is missing tcp/22 service")
  service = list(services)[0]
  service_name = service['name']

  if ip_name!=service_name:
    warn(vm_name, "ip_name and service_name differ")

  if '.' in vm_name and vm_name != ip_name:
    warn(vm_name, "differs from", ip_name)

 
  #vm['custom_fields']['fqdn'] = ip_name
  #vm.save()
  #ip.dns_name = ip_name


  #print(vm.name, "->", vm_name)
  #vm.name = "vm-"+vm_id
  #vm.save()


