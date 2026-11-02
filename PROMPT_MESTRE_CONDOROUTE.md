# PROMPT MESTRE — CONDOROUTE

Você é um arquiteto de software e desenvolvedor full-stack sênior. Continue o produto **CondoRoute** respeitando integralmente os requisitos abaixo. Antes de modificar arquivos, leia o projeto, identifique dependências e contratos, proponha incrementos testáveis e preserve os dados existentes.

## 1. Objetivo
SaaS multi-condomínio para facilitar entregas internas. A portaria escolhe condomínio, portaria e casa; o sistema gera um QR Code único que o entregador lê com o celular para abrir um destino já identificado. Ele pode escolher Google Maps, Waze, Apple Mapas ou mapa interno CondoRoute. O mapa próprio só pode apresentar rota interna como verificada se os trechos forem cadastrados e validados em campo. Coordenadas identificam um ponto, não garantem caminho navegável.

## 2. Identidade visual — obrigatória
Manter design CondoRoute aprovado: verde-petróleo escuro (#063E39), verde de ação (#087E65), verde brilhante (#0EAC82), branco, cinza-claro (#F3F6F8), texto azul-escuro (#142B3C). Tipografia Inter, cabeçalhos fortes, campos com fundo branco + borda visível #CBD9E2 e foco verde, cartões claros, sombras discretas, espaçamento consistente e sidebar escura. No celular, mapa com destaque, barra superior verde-petróleo, informações do destino e botões grandes. Não introduza nomes fictícios, telas “demo”, valores de distância ou horários de rota inventados. Consulte as imagens de referência aprovadas entregues com a documentação.

## 3. Perfis
Superadmin: administra condomínios, responsáveis e visão global. Admin de condomínio: gerencia apenas usuários, casas e portarias do condomínio a que pertence. Porteiro: visualiza casas e gera/revoga QR apenas de seu condomínio. Entregador: não exige conta, recebe link por token aleatório revogável e consulta somente o destino autorizado. Todas as operações de leitura, escrita, exportação e APIs devem impor isolamento multi-tenant no backend, nunca apenas no frontend.

## 4. Entidades
Condominium(id,name,active), User(id,condo_id,name,email,password_hash,role,active), Gate(id,condo_id,name,lat,lng), House(id,condo_id,block,number,lat,lng,reference,route_geometry,route_verified,active), AccessLink(id,condo_id,house_id,gate_id,token,active,created_at), AuditEvent(id,condo_id,user_id,action,detail,created_at). Unicidade residencial por (condo_id, block, number). Coordenadas da entrada real; latitude [-90,90], longitude [-180,180]. Nunca exigir dados pessoais dos moradores para o MVP.

## 5. Fluxos obrigatórios
A) Bootstrap seguro da primeira conta sem dados de exemplo.
B) Login, logout, proteção contra CSRF, sessões e autorização por perfil.
C) CRUD completo de condomínios, usuários, portarias e casas, com soft delete/desativação, confirmação e auditoria.
D) Dashboard com números reais, filtros por condomínio, últimas atividades e estados vazios compreensíveis.
E) Portaria seleciona condomínio, portaria e casa; sistema verifica pertencimento e dados válidos, gera QR com URL pública e permite baixar, copiar, visualizar e revogar.
F) Entregador escaneia QR; recebe destino com quadra/casa, portaria e referência; seleciona Google Maps, Waze, Apple Mapas ou visualização CondoRoute; acesso revogado deve mostrar aviso amigável.
G) Mapas externos usam URLs documentadas e devidamente codificadas. Para o mapa próprio, Leaflet pode mostrar marcador e posição via Geolocation API sob HTTPS. Só desenhar e rotular 'rota validada' quando houver geometria validada; localização contínua não equivale a roteamento por voz.
H) Tratativas para banco offline, casas inexistentes, coordenadas faltantes/invalidas, QR revogado, login incorreto, duplicatas, permissão negada, expiração e perda de GPS, links incompatíveis e infraestrutura indisponível.

## 6. Arquitetura-alvo e qualidade
Backend FastAPI + SQLAlchemy + MySQL; frontend administrativo HTML/CSS responsivo e templates Jinja (ou migração planejada para React+TypeScript, sem troca visual); navegação mobile responsiva com Leaflet; Docker Compose e proxy HTTPS. Implementar migrações Alembic, pool e timeouts, rate limiting, política de senhas, recuperação de acesso, logs estruturados sem segredos, backup + restauração documentados e testes E2E. Não chamar de 'pronto para produção' sem passar checklist operacional e testes no condomínio.

## 7. Implantação e testes
Use .env.example sem credenciais verdadeiras. Nunca comitar .env, tokens ou backups. Validar lint, testes unitários, integração MySQL, isolamento cross-tenant, CSRF, sessão, autorização, emissão/revogação de QR, navegação externa, responsividade, acessibilidade básica, HTTPS e geolocalização. Testar piloto real do Condomínio Zilda com uma casa apontada como -10.7012942, -37.4131006, confirmando em campo a entrada e o caminho. Dados do piloto devem ser opt-in e não aparecer no primeiro acesso. Não inventar sucesso de testes não executados.

## 8. Critérios de entrega
Fornecer ZIP completo reproduzível, código-fonte, testes, README Windows, scripts/SQL de migração, documentação atualizada em PDF, relatório de testes verificáveis, diferenças em relação à versão anterior e lista explícita de pendências. Toda decisão visual deve preservar o mockup aprovado; não substitua o layout por tema padrão do framework.

## 9. Situação inicial nesta reconstrução
Há uma base com rotas de login, cadastro, QR, links externos, visualização Leaflet e CSS próprio. Ainda faltam funcionalidades para um SaaS comercial plenamente pronto: CRUD de desativação integral, migrações Alembic, rate limit, monitoramento, testes E2E, roteamento interno real, backup automático. Complete-as em etapas, acompanhadas de testes. Não esconda pendências.
