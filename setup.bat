@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   INFINITY INMOBILIARIA - Instalacion
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] No se encontro Python. Instalalo desde https://www.python.org/downloads/
  echo         Durante la instalacion, marca la opcion "Add Python to PATH".
  pause
  exit /b 1
)

echo Creando entorno virtual...
python -m venv venv
if errorlevel 1 ( echo [ERROR] No se pudo crear el entorno virtual. & pause & exit /b 1 )

echo Instalando dependencias (puede tardar unos minutos)...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 ( echo [ERROR] Fallo la instalacion de dependencias. & pause & exit /b 1 )

echo.
echo ============================================================
echo   Instalacion completa.
echo   Hace doble clic en "iniciar.bat" para abrir la aplicacion.
echo ============================================================
pause
