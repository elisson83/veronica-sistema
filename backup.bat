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

echo [1/3] Salvando no GitHub...
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

echo [2/3] Backup local nos HDs (G: arena x  e  E: Roberta)...
python organizar.py backup
echo.

echo [3/3] Verificando destinos...
if exist G:\Backup_Veronica (
    echo [HD G: arena x]  OK - encontrado
) else (
    echo [HD G: arena x]  AVISO - HD nao encontrado
)
if exist E:\Backup_Veronica (
    echo [HD E: Roberta]  OK - encontrado
) else (
    echo [HD E: Roberta]  AVISO - HD nao encontrado
)

echo.
echo ================================================
echo    BACKUP CONCLUIDO!
echo ================================================
echo.
echo   GitHub        : https://github.com/elisson83/veronica-ia
echo   HD G: arena x : G:\Backup_Veronica\
echo   HD E: Roberta : E:\Backup_Veronica\
echo.
pause
