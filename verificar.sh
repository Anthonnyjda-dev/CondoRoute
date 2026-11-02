#!/usr/bin/env bash
set -Eeuo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERRO: Docker não foi encontrado."
  exit 1
fi

echo "===== CONTÊINERES ====="
docker compose ps -a

echo
echo "===== ÚLTIMOS LOGS DA APLICAÇÃO ====="
docker compose logs --tail=80 web

echo
echo "Para acompanhar continuamente: docker compose logs -f web"
echo "Use Ctrl+C para sair dos logs; os contêineres continuarão ativos."
