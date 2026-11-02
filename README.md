# CondoRoute

Sistema web para cadastrar condomínios, portarias e residências e gerar QR Codes revogáveis. O entregador acessa uma página pública com o destino, referências, mapa e atalhos para Google Maps, Waze e Apple Mapas.

Esta versão inicia sem condomínios ou dados fictícios. Os registros reais devem ser cadastrados pelo painel administrativo.

## Por onde começar

Leia os arquivos nesta ordem:

1. Este `README.md`, que apresenta o projeto e suas limitações.
2. O guia do seu sistema operacional:
   - [Windows 11, VS Code e CMD](docs/01_GUIA_WINDOWS_CMD.md)
   - [Fedora e outras distribuições Linux](docs/02_GUIA_LINUX.md)
3. [Recuperação do banco](docs/03_RECUPERAR_BANCO.md), somente quando houver erro de senha em um volume MySQL existente.
4. [Prompt mestre do CondoRoute](docs/04_PROMPT_MESTRE_CONDOROUTE.md), usado como referência interna da reconstrução.

O [índice da documentação](docs/README.md) explica a finalidade de cada arquivo.

## Início rápido

### Linux

```bash
chmod +x iniciar.sh verificar.sh
./iniciar.sh
```

### Windows 11 — terminal CMD

```bat
iniciar.cmd
```

Depois, acesse:

```text
http://localhost:8000
```

O e-mail inicial é `admin@condoroute.local`. A senha é criada automaticamente e fica na variável `ADMIN_PASSWORD` do arquivo `.env`.

Se o `.env` já existir, os inicializadores o preservam e não trocam as credenciais existentes.

## Verificação e logs

### Linux

```bash
./verificar.sh
```

### Windows

```bat
verificar.cmd
```

Também é possível consultar diretamente:

```bash
docker compose ps
docker compose logs --tail=80 web
docker compose logs -f web
```

Ao usar `docker compose logs -f web`, pressione `Ctrl+C` para sair dos logs. Os contêineres continuarão ativos.

## Estrutura principal

```text
CondoRoute/
├── app/                    # aplicação FastAPI, páginas e arquivos estáticos
├── docs/                   # guias e documentação do projeto
├── referencias_visuais/    # imagens de referência da interface
├── scripts/                # automação de configuração
├── tests/                  # testes automatizados
├── .env.example            # modelo das variáveis de ambiente
├── compose.yaml            # serviços web e MySQL
├── Dockerfile              # imagem da aplicação
├── iniciar.cmd             # inicialização no Windows
├── iniciar.sh              # inicialização no Linux
├── requirements.txt        # dependências Python
├── verificar.cmd           # diagnóstico no Windows
└── verificar.sh            # diagnóstico no Linux
```

Arquivos executáveis e de infraestrutura permanecem na raiz porque são usados diretamente pelos comandos de instalação. A pasta `docs/` guarda somente documentação.

## Funcionalidades

- autenticação por sessão com senhas PBKDF2 e proteção CSRF;
- perfis `superadmin`, `admin` e `porter`;
- filtragem dos dados por condomínio;
- cadastro de condomínios, portarias, residências e usuários;
- edição de residências;
- geração de QR Code com token público não sequencial;
- revogação, reativação e exclusão de links;
- registro de eventos básicos de auditoria;
- atalhos para Google Maps, Waze e Apple Mapas;
- mapa Leaflet e suporte opcional à localização do navegador;
- interface responsiva em HTML/CSS com FastAPI;
- MySQL executado com Docker Compose.

## Banco e variáveis de ambiente

Na primeira execução, o sistema cria um `.env` com credenciais aleatórias e inicia um volume persistente do MySQL. Não compartilhe o `.env` nem envie suas credenciais para o GitHub.

As tabelas são criadas com `SQLAlchemy.create_all`. O projeto ainda não possui migrações versionadas com Alembic.

> Nunca execute `docker compose down -v` em uma instalação com dados importantes. A opção `-v` apaga o volume do MySQL.

## Acesso pelo celular e QR Code

A configuração local utiliza `http://localhost:8000` e publica a aplicação somente para o próprio computador. Em um celular, `localhost` aponta para o próprio celular, não para o computador que executa o CondoRoute.

Para um piloto em aparelho real, ainda será necessário disponibilizar um endereço acessível ao celular e ajustar `PUBLIC_BASE_URL`. Em produção, deve-se utilizar HTTPS, inclusive para os recursos de geolocalização do navegador.

## Piloto do Condomínio Zilda

A coordenada informada pela equipe para uma residência é `-10.7012942, -37.4131006`. Ela não é inserida automaticamente. Condomínio, portaria, quadra, número, referência e coordenadas devem ser verificados antes do cadastro.

O QR Code leva à coordenada registrada, mas não garante que serviços externos possuam o mapeamento das vias internas do condomínio.

## Limitações atuais

Esta é uma versão de desenvolvimento e ainda não é uma implantação de produção auditada. Entre os itens pendentes estão:

- publicação HTTPS e configuração de domínio;
- migrações versionadas do banco;
- recuperação de senha;
- bloqueio ou limitação de tentativas de login;
- gerenciamento completo do ciclo de vida dos usuários;
- backups automáticos e procedimento de restauração testado;
- observabilidade e monitoramento;
- testes E2E em navegadores;
- políticas de privacidade e tratamento de dados;
- interface para cadastrar a geometria das rotas internas;
- algoritmo próprio de roteamento interno e navegação por voz.

Um trajeto interno só é desenhado quando existe uma geometria cadastrada e `route_verified=true`.

## Desenvolvimento sem Docker

Para testes locais com Python:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='sqlite:///./condoroute.db'
export ADMIN_EMAIL='admin@condoroute.local'
export ADMIN_PASSWORD='uma-senha-com-12-ou-mais-caracteres'
export SESSION_SECRET='segredo-local-de-desenvolvimento'
python -m pytest -q
uvicorn app.main:app --reload
```

No Windows, a ativação e a definição das variáveis de ambiente usam comandos diferentes; para a execução normal, prefira `iniciar.cmd` com Docker.
