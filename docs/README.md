# Documentação do CondoRoute

## Ordem recomendada de leitura

1. Leia primeiro o [`README.md`](../README.md) da raiz para entender o projeto, suas funcionalidades e limitações.
2. Siga o guia correspondente ao seu sistema operacional:
   - [`01_GUIA_WINDOWS_CMD.md`](01_GUIA_WINDOWS_CMD.md) — Windows 11, VS Code e CMD.
   - [`02_GUIA_LINUX.md`](02_GUIA_LINUX.md) — Fedora e outras distribuições Linux.
3. Consulte [`03_RECUPERAR_BANCO.md`](03_RECUPERAR_BANCO.md) somente se o MySQL apresentar erro de senha ou se for necessário preservar um banco existente.
4. Use [`04_PROMPT_MESTRE_CONDOROUTE.md`](04_PROMPT_MESTRE_CONDOROUTE.md) como referência interna do contexto e dos requisitos usados na reconstrução do sistema.

## O que não pertence à pasta `docs`

- `requirements.txt`: dependências Python usadas na construção da aplicação.
- `iniciar.cmd` e `verificar.cmd`: atalhos executáveis para Windows.
- `iniciar.sh` e `verificar.sh`: atalhos executáveis para Linux.
- `compose.yaml` e `Dockerfile`: infraestrutura Docker.
- `.env.example`: modelo das variáveis de ambiente.

Esses arquivos permanecem na raiz porque são usados diretamente pelos comandos de instalação e execução.
