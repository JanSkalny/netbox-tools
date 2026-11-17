#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
branch="$(git -C "$script_dir" branch --show-current)"

if [[ -z "$branch" ]]; then
    branch="$(git -C "$script_dir" rev-parse --short HEAD)"
fi

# Docker tags cannot contain slashes (common in branch names).
tag="${branch//\//-}"

docker buildx build \
    --platform linux/arm64,linux/amd64 \
    --load \
    --tag "janskalny/netbox-tools:$tag" \
    --tag janskalny/netbox-tools:latest \
    "$script_dir"

printf 'Built janskalny/netbox-tools:%s and janskalny/netbox-tools:latest\n' "$tag"
