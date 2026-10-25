# netbox-tools
Collection of assorted tools and CLI scripts for NetBox. [1]

## Installation and requirents
1. create and enter python environment for running the scripts
```
python3 -m venv venv
. ./venv/bin/activate
pip3 install -r requirements.txt # [2]
```
2. Create your "env" file. (see. `env.example`)
3. `. ~/Path/To/netbox-tools/env`
4. ...
5. Profit!

### Docker

Build the image and load the helper function:

```bash
./build.sh
source ./activate.example
```

The helper forwards the NetBox environment variables from your current shell.
Run any tool by passing its script name and arguments:

```bash
netbox-tools netbox_find_device.py --help
netbox-tools netbox_add_service.py vm-example-1 service.example.com tcp/80
```

By default the helper uses `netbox-tools:latest`. Set `NETBOX_TOOLS_TAG` to run a
branch-tagged image produced by `build.sh`.

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

### `netbox_create_tenant_group.py`
 - create a tenant group; its slug defaults to the lowercase name with spaces replaced by dashes
 - example: `./netbox_create_tenant_group.py "Example Group"`

### `netbox_create_tenant.py`
 - create a tenant, optionally assigning it to a tenant group by slug
 - example: `./netbox_create_tenant.py "Example Tenant" --tenant-group example-group`

### Filtering list commands
 - `netbox_list_tenants.py`, `netbox_list_tenant_groups.py`, `netbox_list_ips.py`, `netbox_list_prefixes.py`, `netbox_list_vrfs.py`, `netbox_list_contacts.py`, `netbox_list_vms.py`, and `netbox_list_vms_fqdns.py` accept repeatable `--filter KEY=VALUE` options
 - filters use NetBox REST API names; custom fields use the `cf_` prefix
 - boolean custom-field filters accept `1`/`0`, `true`/`false`, `yes`/`no`, or `on`/`off`
 - custom-field negation uses the `__n` suffix and includes objects where the field is unset
 - `netbox_list_custom.py` is not a collection query: it lists fields on one identified object, so API filters do not apply

### `netbox_list_tenants.py`
 - list tenant slugs (or names with `--names`), optionally including their group slugs with `--with-groups`
 - example: `./netbox_list_tenants.py --filter cf_void_wazuh=1`

### `netbox_create_ip.py`
 - create an IPv4 or IPv6 address and print the new object's ID
 - optionally assign a DNS name, description, tenant slug, VRF name, and existing tags
 - repeat `--tag` to assign multiple tags; tags are selected by slug and must already exist
 - use `-v` to trace each NetBox API request with its status code and duration
 - example: `./netbox_create_ip.py 192.0.2.10/24 --name host.example.com --tenant example-tenant --vrf example-vrf --tag production`

### `netbox_list_ips.py`
 - list IP addresses, optionally filtered by tenant slug or repeatable NetBox API filters
 - use `--output address|id|json` to select the output; the default is `address`
 - example: `./netbox_list_ips.py --tenant example-tenant --filter status=active --output json`

### `netbox_create_prefix.py`
 - create an IPv4 or IPv6 prefix for a tenant and print the new object's ID
 - optionally assign a description, VLAN number, VRF name, and existing tags
 - repeat `--tag` to assign multiple tags; tags are selected by slug and must already exist
 - example: `./netbox_create_prefix.py 192.0.2.0/24 example-tenant --description "Example network" --vlan 100 --vrf example-vrf --tag production --tag customer-facing`

### `netbox_list_prefixes.py`
 - list prefix CIDRs, optionally filtered by tenant slug and one existing tag slug
 - example: `./netbox_list_prefixes.py --tenant example-tenant --tag production`

### `netbox_list_vrfs.py`
 - list VRF names, optionally filtered by tenant slug
 - example: `./netbox_list_vrfs.py --tenant example-tenant`

### `netbox_create_vrf.py`
 - create a VRF, optionally assigning it to a tenant by slug, and print the new object's ID
 - example: `./netbox_create_vrf.py production --tenant example-tenant`

### Custom fields
 - `netbox_get_custom.py TYPE IDENTIFIER FIELD` prints one custom-field value
 - `netbox_list_custom.py TYPE IDENTIFIER [FIELD]` lists field slugs and values, sorted by slug
 - `netbox_set_custom.py TYPE IDENTIFIER FIELD VALUE` sets a field; use `--clear` instead of `VALUE` to clear it, or `-n` to only show the requested change
 - supported types are `ip`, `prefix`, `tenant`, `vm`, `device`, and `vlan`
 - identifiers may be numeric object IDs; natural identifiers are also accepted (address/CIDR, tenant slug/name, or VM/device/VLAN name)
 - object and multi-object custom-field values are supplied and displayed as names/slugs rather than descriptions; comma-separated and JSON-array values are accepted for multi-value fields
 - examples: `./netbox_get_custom.py vm vm-example-1 storage_type`, `./netbox_set_custom.py vm vm-example-1 storage_device storage-1`, `./netbox_list_custom.py tenant example-tenant`

### `netbox_update_tenant_group.py`
 - update the name or slug of a tenant group selected by its current slug
 - example: `./netbox_update_tenant_group.py example-group --new-name "Renamed Group"`

### `netbox_update_tenant.py`
 - update the name, slug, or tenant group of a tenant selected by its current slug
 - example: `./netbox_update_tenant.py example-tenant --new-tenant-group another-group`

### `netbox_list_contacts.py`
 - list contacts, displaying their names by default
 - optionally filter contacts by tenant slug with `--tenant`
 - use `--output name|phone|email|id|json` to select the output
 - example: `./netbox_list_contacts.py --tenant example-tenant --output email`

### `netbox_find_contact.py`
 - find a contact by exact name, phone, or email, displaying its ID by default
 - use `--output name|phone|email|id|json` to select the output
 - example: `./netbox_find_contact.py "Jane Example" --output json`

### `netbox_create_contact.py`
 - create a contact; only `--name` is required
 - optionally accepts `--phone`, `--email`, and `--description`
 - prints the new contact's ID
 - example: `./netbox_create_contact.py --name "Jane Example" --phone "+421900123456" --email "jane@example.com" --description "Primary contact"`

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
