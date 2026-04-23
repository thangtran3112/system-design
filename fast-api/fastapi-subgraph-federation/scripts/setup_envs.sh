#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

setup_service() {
  local service_path="$1"

  python3 -m venv "${service_path}/.venv"
  "${service_path}/.venv/bin/pip" install --upgrade pip
  "${service_path}/.venv/bin/pip" install -r "${service_path}/requirements.txt"
}

setup_service "${ROOT_DIR}/services/users"
setup_service "${ROOT_DIR}/services/todos"

printf "Done. Virtual environments created for users and todos.\n"
