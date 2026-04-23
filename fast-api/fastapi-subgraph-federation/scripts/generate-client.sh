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

# Step 1: Strip Apollo Federation directives → clean client schema
printf "=== Step 1: Strip federation directives ===\n"
python3 scripts/strip_federation.py "${SUPERGRAPH}" > "${CLIENT_SCHEMA}"
printf "  -> %s\n" "${CLIENT_SCHEMA}"

# Step 2: Auto-generate .graphql operation files from schema
printf "\n=== Step 2: Generate GraphQL operations ===\n"
node scripts/generate-operations.mjs

# Step 3: Generate TypeScript SDK (graphql-codegen)
printf "\n=== Step 3: Generate TypeScript SDK ===\n"
npx graphql-codegen --config codegen.ts
printf "  -> generated/typescript/sdk.ts\n"

# Step 4: Generate Python SDK (ariadne-codegen)
printf "\n=== Step 4: Generate Python SDK ===\n"
.venv/bin/ariadne-codegen
printf "  -> tests/supergraph_client/\n"

printf "\n✓ All SDK clients generated successfully.\n"
