#!/usr/bin/env bash
set -Eeuo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

echo "=========================================="
echo " CondoRoute - Linux"
echo "=========================================="

if ! command -v docker >/dev/null 2>&1; then
  echo "ERRO: Docker não foi encontrado. Instale e inicie o Docker."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "ERRO: o serviço do Docker não está iniciado ou seu usuário não possui permissão."
  echo "No Fedora, tente: sudo systemctl enable --now docker"
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "ERRO: o plugin Docker Compose não foi encontrado."
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "Criando .env com credenciais aleatórias..."
  docker run --rm -v "$PWD:/project:Z" -w /project \
    python:3.12-slim python scripts/setup_env.py
fi

echo
echo "Construindo e iniciando o CondoRoute..."
docker compose up --build -d

echo
echo "Conferindo os contêineres..."
docker compose ps

echo
echo "CondoRoute iniciado: http://localhost:8000"
echo "A senha inicial está em ADMIN_PASSWORD no arquivo .env."
echo "Se houver problema, execute: ./verificar.sh"
