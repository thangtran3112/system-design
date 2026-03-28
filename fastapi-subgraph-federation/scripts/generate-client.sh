#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

SUPERGRAPH="router/supergraph.graphql"
CLIENT_SCHEMA="graphql/client-schema.graphql"

if [ ! -f "${SUPERGRAPH}" ]; then
  printf "Error: %s not found. Run scripts/compose_supergraph.sh first.\n" "${SUPERGRAPH}" >&2
  exit 1
fi

# Strip Apollo Federation directives to produce a client-facing schema
python scripts/strip_federation.py "${SUPERGRAPH}" > "${CLIENT_SCHEMA}"
printf "Stripped federation directives → %s\n" "${CLIENT_SCHEMA}"

# Generate the typed Python client
ariadne-codegen
printf "Generated SDK client → tests/supergraph_client/\n"
