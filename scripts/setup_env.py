from pathlib import Path
import secrets, sys
p=Path('/project/.env')
if p.exists():
    print('O arquivo .env ja existe. Nao foi sobrescrito.')
    print('Se o MySQL antigo tiver outra senha, consulte RECUPERAR_BANCO.md.')
    sys.exit(0)
def token(n=24): return secrets.token_hex(n)
p.write_text('\n'.join([
    'COMPOSE_PROJECT_NAME=condoroute_cmd11',
    'APP_ENV=development',
    'MYSQL_USER=condoroute',
    'MYSQL_DATABASE=condoroute',
    f'MYSQL_PASSWORD={token()}',
    f'MYSQL_ROOT_PASSWORD={token()}',
    f'SESSION_SECRET={token(48)}',
    'SESSION_HTTPS=false',
    'ADMIN_EMAIL=admin@condoroute.local',
    f'ADMIN_PASSWORD={token(18)}',
    'PUBLIC_BASE_URL=http://localhost:8000',
    '']) , encoding='utf-8')
print('Arquivo .env criado com sucesso.')
print('Login: admin@condoroute.local')
print('Para consultar sua senha local, abra o .env e veja ADMIN_PASSWORD.')
print('Nao compartilhe o .env.')
