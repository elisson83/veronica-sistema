@echo off
title Backup Completo - Veronica IA
chcp 65001 > nul
echo.
echo ================================
echo    BACKUP COMPLETO VERONICA IA
echo ================================
echo.

cd /d %USERPROFILE%\Desktop\veronica

echo [1/4] Salvando no GitHub...
git add .
git commit -m "Backup automatico %date% %time%"
git push origin main
echo.

echo [2/4] Backup da Veronica...
python organizar.py 3
echo.

echo [3/4] Backup do PainelGest...
python organizar.py 2
echo.

echo [4/4] Concluido!
echo.
echo GitHub atualizado
echo HD (E:) atualizado
echo Pen Drive (D:) atualizado
echo.
pause