# CondoRoute — Windows 11, VS Code e CMD

1. Instale e abra o Docker Desktop.
2. Extraia o ZIP em uma pasta nova.
3. Abra a pasta raiz do projeto no VS Code.
4. Selecione o terminal **CMD**.
5. Execute:

```bat
iniciar.cmd
```

6. Abra `http://localhost:8000`.
7. Use o e-mail `admin@condoroute.local`. Consulte a senha na variável `ADMIN_PASSWORD` do arquivo `.env`.
8. Se houver algum problema, execute:

```bat
verificar.cmd
```

O script cria o `.env` automaticamente quando ele ainda não existe e depois inicia os serviços com Docker Compose.

> Não remova volumes de um MySQL que contenha dados importantes. O comando `docker compose down -v` apaga o banco local do projeto.
