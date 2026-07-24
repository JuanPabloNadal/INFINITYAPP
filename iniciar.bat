@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
  echo No se encontro el entorno. Ejecuta primero "setup.bat".
  pause
  exit /b 1
)
echo ============================================================
echo  Infinity Inmobiliaria  (modo consola)
echo ------------------------------------------------------------
echo  Para el uso diario SIN esta ventana, usa "iniciar.vbs"
echo  (arranca oculto, con un icono en la bandeja del sistema).
echo ------------------------------------------------------------
echo  La app se abrira en http://127.0.0.1:5000
echo  Para cerrarla: cierra esta ventana.
echo ============================================================
set FLASK_DEBUG=0
venv\Scripts\python.exe run.py
pause
