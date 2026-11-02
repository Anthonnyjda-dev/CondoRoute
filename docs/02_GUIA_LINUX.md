# CondoRoute — Linux

Este guia serve para Fedora e outras distribuições Linux que já tenham Docker Engine e o plugin Docker Compose instalados.

## 1. Abrir o projeto

Extraia o ZIP, abra um terminal na pasta raiz do projeto e confirme que estes arquivos aparecem nela:

```text
compose.yaml
Dockerfile
iniciar.sh
requirements.txt
```

## 2. Dar permissão aos scripts

Normalmente o ZIP já preserva essa permissão. Se o terminal apresentar `Permissão negada`, execute:

```bash
chmod +x iniciar.sh verificar.sh
```

## 3. Iniciar o sistema

```bash
./iniciar.sh
```

O script verifica o Docker, cria o `.env` com credenciais aleatórias quando necessário, constrói as imagens e inicia os serviços.

Abra no navegador:

```text
http://localhost:8000
```

O usuário inicial é `admin@condoroute.local`. Consulte a variável `ADMIN_PASSWORD` no arquivo `.env` para encontrar a senha inicial.

## 4. Verificar o sistema

```bash
./verificar.sh
```

Para acompanhar os logs continuamente:

```bash
docker compose logs -f web
```

Use `Ctrl+C` para sair dos logs. Isso não encerra os contêineres.

## Comandos úteis

```bash
# Consultar o estado
docker compose ps

# Parar sem apagar o banco
docker compose stop

# Iniciar novamente
docker compose start

# Reconstruir depois de alterar o código
docker compose up --build -d

# Exibir os últimos logs
docker compose logs --tail=80 web
```

> Não execute `docker compose down -v` se houver dados importantes. A opção `-v` apaga o volume que armazena o banco MySQL.

## Acesso por celular

Na configuração atual, o sistema é acessível apenas no próprio computador. O endereço `localhost` presente no QR Code também aponta para o próprio aparelho que o lê. O acesso por celular exigirá uma configuração de rede ou publicação HTTPS específica, que ainda não faz parte da inicialização local.
