@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo  CondoRoute - Windows 11 / CMD
 echo ==========================================
where docker >nul 2>&1
if errorlevel 1 (
 echo ERRO: Docker nao foi encontrado. Abra o Docker Desktop.
 pause
 exit /b 1
)
docker info >nul 2>&1
if errorlevel 1 (
 echo ERRO: Docker Desktop nao esta iniciado.
 pause
 exit /b 1
)
if not exist .env (
 echo Criando arquivo .env com Python dentro do Docker...
 docker run --rm -v "%CD%:/project" -w /project python:3.12-slim python scripts/setup_env.py
 if errorlevel 1 (echo ERRO ao criar .env & pause & exit /b 1)
)
echo.
echo Construindo e iniciando CondoRoute...
docker compose up --build -d
if errorlevel 1 (echo ERRO ao iniciar Docker Compose & pause & exit /b 1)
echo.
echo Conferindo containers...
docker compose ps
echo.
echo Acesse: http://localhost:8000
echo Se o web reiniciar, execute: verificar.cmd
pause
