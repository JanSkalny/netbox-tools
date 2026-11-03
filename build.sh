#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
branch="$(git -C "$script_dir" branch --show-current)"

if [[ -z "$branch" ]]; then
    branch="$(git -C "$script_dir" rev-parse --short HEAD)"
fi

# Docker tags cannot contain slashes (common in branch names).
tag="${branch//\//-}"

docker build \
    --tag "netbox-tools:$tag" \
    --tag netbox-tools:latest \
    "$script_dir"

printf 'Built netbox-tools:%s and netbox-tools:latest\n' "$tag"
