# CondoRoute — reconstrução da aplicação

Sistema web para cadastro de condomínios, portarias e residências e geração de QR Code revogável. Interface pública do entregador com Google Maps, Waze, Apple Mapas e visualização Leaflet. **Instalação limpa: sem condomínios fictícios ou dados de demonstração.**

## Instalação no Windows 11, VS Code e terminal CMD (sem PowerShell)

1. Extraia o ZIP em **uma pasta nova** e abra essa pasta no VS Code.
2. Abra o Docker Desktop e aguarde inicializar.
3. No **CMD** (terminal do VS Code), execute `iniciar.cmd`.
4. O instalador usa a imagem Python do Docker para criar `.env` com credenciais aleatórias, sem exigir Python nem PowerShell instalados no Windows. Depois inicia `docker compose up --build -d`.
5. Acesse `http://localhost:8000`. Login: `admin@condoroute.local`; a senha inicial está no arquivo `.env` na variável `ADMIN_PASSWORD`.
6. Se houver problema, execute `verificar.cmd` e observe o erro nos logs.

O novo ambiente utiliza `COMPOSE_PROJECT_NAME=condoroute_cmd11` para **não reutilizar automaticamente** o volume MySQL das tentativas anteriores. **Não apaga nem migra** o banco antigo. Caso já exista `.env` nesta pasta, ele será preservado: o instalador não troca senhas existentes.

Não compartilhe seu `.env` ou logs com credenciais. **Nunca execute `docker compose down -v` em uma instalação com dados importantes.**

**Limitação:** esta é uma versão para teste local; a operação pública ainda exige HTTPS, hospedagem, backups, políticas de acesso e testes de campo.

**Celular:** `localhost` não funciona em outro aparelho. Para abrir a página de QR em um celular, é necessário um endereço público acessível ao aparelho, geralmente com HTTPS para habilitar GPS no navegador.

## Funcionalidades nesta edição

- Autenticação por sessão, senhas PBKDF2, CSRF em formulários, cookies seguros configuráveis, perfis `superadmin`, `admin`, `porter`.
- Filtragem de dados por condomínio para consultas do painel, cadastros e geração de links.
- Cadastro de condomínios, portarias e casas; edição de casas; criação de contas administrativas e de porteiros.
- QR aleatório revogável; as casas não são expostas por ID sequencial público; consulta pública controlada pelo token.
- Destino e referências na interface pública, abertura dos três navegadores e mapa de coordenadas Leaflet. GPS de navegador opcional.
- Layout responsivo próprio com HTML/CSS e FastAPI; não utiliza Streamlit.

## Limites importantes / antes de publicar

O projeto **não é uma implantação de produção auditada**: não foram implementados migrações Alembic, recuperação de senha, bloqueio/rate limit por tentativas de login, alterações e desativação de usuários, gestão de cobrança, agendamento de backups, operação de observabilidade, testes E2E em navegadores ou aplicação de políticas de privacidade. As rotas internas só são exibidas quando houver geometria verificada já cadastrada; esta edição **não** possui UI para cadastrar essa geometria nem algoritmo de roteamento interno ou voz. Configure proxy HTTPS, políticas de backup e monitoração antes de exposição pública.

Banco: as tabelas são criadas por `create_all` na inicialização — **não constitui migração versionada**. Recomenda-se usar banco novo nesta reconstrução, pois o esquema é diferente da V5. Não substitua o banco anterior sem backup.

## Testar sem Docker

`pip install -r requirements.txt`; defina `DATABASE_URL=sqlite:///./condoroute.db`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `SESSION_SECRET`; `python -m pytest -q`; `uvicorn app.main:app --reload`.

## Piloto Zilda

A coordenada informada pela equipe para uma casa é `-10.7012942, -37.4131006`. Não é inserida automaticamente: cadastre condomínio e casa reais no painel, verificando quadra, número e entrada. O QR não comprova que o mapa externo tenha vias internas roteáveis.


## Atualização V6 — Fluxos e correção do Leaflet

- Portaria: condomínio → residência filtrada → portaria de origem → QR.
- Links: 10 registros por página; revogar, reativar e excluir, preservando evento de auditoria.
- Condomínios: gestão individual de portarias e residências; usuários em seção separada.
- Tela do entregador: mapa Leaflet isolado em `courier-map.css`, CSS do Leaflet carregado antes dos estilos da aplicação, `invalidateSize` e `ResizeObserver`.
- Dados legados: este pacote não modifica nem exclui volumes MySQL. Não execute `docker compose down -v`.
- Para Windows 11 / terminal CMD: `iniciar.cmd` e `verificar.cmd`. Para atualizar a imagem: `docker compose up --build -d --force-recreate web`.
- Zoom excessivo do navegador pode deixar a interface deliberadamente estreita, mas não deve deslocar os tiles do mapa para fora da sua área.
- A data de cadastro e a referência do *condomínio* não existiam na estrutura original; esses campos não são apresentados como preenchidos até migração própria.
- Um trajeto interno somente é desenhado se houver geometria cadastrada e `route_verified=true`. GPS exige HTTPS no celular.
