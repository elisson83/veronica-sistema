@echo off
title Backup Completo - Veronica IA
chcp 65001 > nul
echo.
echo ================================================
echo    BACKUP COMPLETO — VERONICA IA
echo    %date% %time%
echo ================================================
echo.

cd /d %USERPROFILE%\Desktop\veronica

echo [1/4] Salvando no GitHub...
echo.
git add .
git commit -m "Backup automatico %date% %time%"
git push origin main
if %errorlevel% == 0 (
    echo [GitHub] OK - enviado com sucesso!
) else (
    echo [GitHub] ATENCAO - verifique sua conexao ou credenciais.
)
echo.

echo [2/4] Backup completo da Veronica no HD (E:) e Pen Drive (D:)...
python organizar.py 3
echo.

echo [3/4] Backup do PainelGest no HD (E:) e Pen Drive (D:)...
python organizar.py 2
echo.

echo [4/4] Verificando destinos...
if exist E:\backup_veronica (
    echo [HD E:]       OK - pasta backup_veronica encontrada
) else (
    echo [HD E:]       AVISO - HD nao encontrado ou sem backup anterior
)
if exist D:\backup_veronica (
    echo [Pen Drive D:] OK - pasta backup_veronica encontrada
) else (
    echo [Pen Drive D:] AVISO - Pen Drive nao encontrado ou sem backup anterior
)

echo.
echo ================================================
echo    BACKUP CONCLUIDO!
echo ================================================
echo.
echo   GitHub     : https://github.com/elisson83/veronica-ia
echo   HD (E:)    : E:\backup_veronica\
echo   Pen Drive  : D:\backup_veronica\
echo.
pause
