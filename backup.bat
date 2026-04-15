@echo off
title Backup Verônica IA
color 0A

echo ================================================
echo    BACKUP VERONICA IA - %date% %time%
echo ================================================
echo.

set ORIGEM=C:\Users\%USERNAME%\Desktop\veronica
set PENDRIVE=D:\Backup_Veronica
set HD_EXTERNO=E:\Backup_Veronica

echo [1/3] Salvando no Computador (já está salvo!)
echo ✓ Computador OK!
echo.

echo [2/3] Salvando no Pendrive (D:)...
if exist "D:\" (
    xcopy "%ORIGEM%" "%PENDRIVE%" /E /I /H /Y /Q
    echo ✓ Pendrive OK!
) else (
    echo ✗ Pendrive não encontrado! Conecte o Pendrive e tente novamente.
)
echo.

echo [3/3] Salvando no HD Externo (E:)...
if exist "E:\" (
    xcopy "%ORIGEM%" "%HD_EXTERNO%" /E /I /H /Y /Q
    echo ✓ HD Externo OK!
) else (
    echo ✗ HD Externo não encontrado! Conecte o HD e tente novamente.
)
echo.

echo ================================================
echo    BACKUP CONCLUIDO! %date% %time%
echo ================================================
echo.
pause