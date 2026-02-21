@echo off
docker info >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop is not running. Start Docker Desktop and run this file again.
  pause
  exit /b 1
)

docker compose up --build
pause
