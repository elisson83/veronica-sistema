@echo off
title Verônica IA - Desligando...
chcp 65001 > nul
echo Desligando ecossistema Verônica IA...
echo.

taskkill /f /im python.exe > nul 2>&1
echo Python encerrado!

taskkill /f /im python3.exe > nul 2>&1

taskkill /f /im ollama.exe > nul 2>&1
echo Ollama encerrado!

taskkill /f /im ollama_llama_server.exe > nul 2>&1

wmic process where "name='python.exe'" delete > nul 2>&1

echo.
echo Tudo desligado com sucesso!
timeout /t 2 /nobreak > nul