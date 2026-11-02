# Recuperar senha de um MySQL já existente (sem excluir dados)

Se `condoroute-web-1` reinicia e os logs mostram `Access denied for user 'condoroute'`, a senha do MySQL no volume persistido difere do `.env` atual. **Não use `docker compose down -v`**.

## Opção recomendada para preservar os dados

1. Faça backup do seu banco antes de qualquer alteração.
2. Encontre a senha ROOT que foi usada **na primeira inicialização** desse volume. Trocar `MYSQL_ROOT_PASSWORD` no `.env` não altera o root já criado.
3. No terminal do projeto, execute `docker compose exec db mysql -uroot -p` e informe a senha root antiga quando solicitada (não aparece ao digitar).
4. Dentro do `mysql>` execute o comando abaixo, substituindo a senha pelo valor de `MYSQL_PASSWORD` no `.env` (não cole senhas no chat):

```sql
ALTER USER 'condoroute'@'%' IDENTIFIED BY 'SENHA_ATUAL_DO_MYSQL_PASSWORD';
EXIT;
```

5. Execute `docker compose up -d --force-recreate web` e depois `docker compose logs web --tail=30`.

Se o usuário `condoroute` não existir, pare e confirme os usuários com `SELECT User,Host FROM mysql.user;` como root, em vez de executar comandos de exclusão.

**Sem a senha root original, não é possível corrigir de forma segura apenas trocando o arquivo `.env`.** Você precisará usar uma estratégia de recuperação de credenciais respaldada por backup e acesso administrativo ao banco. Nunca apague o volume se quiser preservar os dados.

## Ambiente novo

Se o volume ainda não existe, execute `powershell -ExecutionPolicy Bypass -File .\setup_windows.ps1` para criar `.env`, depois `docker compose up --build -d`. O MySQL cria automaticamente o usuário e aplica a mesma senha à aplicação.
