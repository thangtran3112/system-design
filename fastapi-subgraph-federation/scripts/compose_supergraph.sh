#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

rover supergraph compose \
  --elv2-license accept \
  --config "${ROOT_DIR}/router/supergraph.yaml" \
  > "${ROOT_DIR}/router/supergraph.graphql"

printf "Composed supergraph to router/supergraph.graphql\n"
