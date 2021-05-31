# netbox-tools
Collection of assorted tools and CLI scripts for NetBox. [1]

## Installation and requirents
1. `pip3 install -r requirements.txt` [2]
2. Create your "env" file. (see. `env.example`)
3. `. ~/Path/To/netbox-tools/env`
4. ...
5. Profit!

## Description and usage
### `netbox_add_if.py`
 - add interface and allocate IP address from VLAN (if specified) 

### `netbox_add_service.py` 
 - add service to specified device
 - example: `./netbox_add_service.py vm-example-1 "service-name.example.com" tcp/80`

### `netbox_set_if_vlans.py`
 - set speicied device or VM interface to trunk mode
 - lookup all VLANs withing given range
 - and tag interface (and it's LAG members) with existing VLANs
 - example: `./netbox_set_if_vlans.py srv-example-1 bond0 1,10,20-39,100`

### `netbox_create_vm.py`
 - create new VM with "eth0" interface, allocate ip address and create tcp/22 service
 - for usage, see `./netbox_create_vm.py -h`

### `netbox_generate_config.py`
 - generate yaml file with config context of specified device or vm

### `netbox_generate_networking.py`
 - generate yaml file with networking configuration of specified device or vm
 - for format, see: ansible-roles-common/linux-networking 

### `netbox_generate_virtual.py`
 - generate yaml file with virtual configuration fo specified vm
 - for format, see: ansible-roles/common/virtual/preseed-ng

### `netbox_generate_ns_zone.py`
 - generate bind zone file for specified domain
 - ip addresses are gathered from devices, VMs, IPs and services with FQDNs
 - example: `./netbox_generate_ns_zone.py example.com`

## Links
[1] https://github.com/netbox-community/netbox
[2] https://pynetbox.readthedocs.io/en/latest/
