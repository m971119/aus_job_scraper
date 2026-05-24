@echo off
cd /d "%~dp0.."
if not exist .env copy .env.example .env
if not exist data mkdir data
docker compose up -d %*
echo Running - frontend: http://localhost:3000
