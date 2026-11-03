#!/usr/bin/env python3

import argparse
import ipaddress
import os
from sys import exit, stderr
from time import perf_counter

import pynetbox


def fail(*messages):
  print(*messages, file=stderr)
  exit(1)


def trace_response(response, *args, **kwargs):
  request = response.request
  duration = response.elapsed.total_seconds()
  print(
    f'{request.method} {response.url} -> {response.status_code} '
    f'in {duration:.3f}s',
    file=stderr,
  )
  return response


def enable_request_tracing(nb):
  nb.http_session.hooks.setdefault('response', []).append(trace_response)


def ip_address(value):
  try:
    return str(ipaddress.ip_interface(value))
  except ValueError as error:
    raise argparse.ArgumentTypeError(str(error)) from error


def find_vrf(nb, identifier):
  matches = [
    vrf for vrf in nb.ipam.vrfs.filter(name=identifier)
    if vrf.name == identifier
  ]
  if not matches:
    fail('no such VRF:', identifier)
  if len(matches) > 1:
    fail('VRF identifier is ambiguous:', identifier)
  return matches[0]


def main():
  parser = argparse.ArgumentParser(description='Create a NetBox IP address.')
  parser.add_argument('address', type=ip_address, help='IPv4 or IPv6 address in CIDR notation')
  parser.add_argument('-n', '--name', help='DNS name')
  parser.add_argument('-d', '--description', help='IP address description')
  parser.add_argument('-t', '--tenant', help='Tenant slug')
  parser.add_argument('-r', '--vrf', help='VRF name')
  parser.add_argument('-g', '--tag', action='append', default=[], help='Existing tag slug (may be repeated)')
  parser.add_argument('-v', '--verbose', action='count', default=0,
                      help='Trace NetBox API requests, status codes, and durations')
  parser.add_argument('-T', '--token', help='NetBox API Token (defaults to NETBOX_TOKEN env)', default=os.getenv('NETBOX_TOKEN'))
  parser.add_argument('-A', '--api-url', help='NetBox API URL (defaults to NETBOX_API_URL env)', default=os.getenv('NETBOX_API_URL'))
  args = parser.parse_args()

  nb = pynetbox.api(args.api_url, token=args.token)
  if args.verbose:
    enable_request_tracing(nb)
    started_at = perf_counter()
  ip_data = {'address': args.address}

  if args.name is not None:
    ip_data['dns_name'] = args.name

  if args.description is not None:
    ip_data['description'] = args.description

  if args.tenant is not None:
    tenant = nb.tenancy.tenants.get(slug=args.tenant)
    if not tenant:
      fail('no such tenant:', args.tenant)
    ip_data['tenant'] = tenant.id

  if args.vrf is not None:
    ip_data['vrf'] = find_vrf(nb, args.vrf).id

  if args.tag:
    tags = []
    for tag_slug in args.tag:
      tag = nb.extras.tags.get(slug=tag_slug)
      if not tag:
        fail('no such tag:', tag_slug)
      tags.append(tag.id)
    ip_data['tags'] = tags

  ip = nb.ipam.ip_addresses.create(ip_data)
  if args.verbose:
    print(f'NetBox API operations completed in {perf_counter() - started_at:.3f}s',
          file=stderr)
  print(ip.id)


if __name__ == '__main__':
  main()
