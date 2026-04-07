@echo off
title Facturacion - Inicio Limpio
echo ============================================
echo   FACTURACION - Inicio con limpieza de cache
echo ============================================
echo.

:: Ir al directorio del proyecto
cd /d %~dp0

:: ── Cerrar instancias anteriores ──
echo [0/5] Cerrando procesos anteriores...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000.*LISTENING" 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8082.*LISTENING" 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)
echo       OK

:: ── Limpiar caches de Python ──
echo [1/5] Limpiando __pycache__...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
echo       OK

:: ── Limpiar cache de pytest ──
echo [2/5] Limpiando .pytest_cache...
if exist .pytest_cache rd /s /q .pytest_cache 2>nul
echo       OK

:: ── Limpiar cache de Streamlit ──
echo [3/5] Limpiando cache de Streamlit...
if exist frontend\.streamlit\cache rd /s /q frontend\.streamlit\cache 2>nul
if exist "%USERPROFILE%\.streamlit\cache" rd /s /q "%USERPROFILE%\.streamlit\cache" 2>nul
echo       OK

:: ── Limpiar archivos .pyc ──
echo [4/5] Limpiando archivos .pyc...
del /s /q *.pyc 2>nul
echo       OK

echo.
echo [5/5] Iniciando servicios...
echo.

:: ── Iniciar Django en segundo plano ──
echo   >> Django backend en http://127.0.0.1:8000
start "Django-Backend" cmd /k "cd /d %~dp0 && venv\Scripts\activate && python manage.py runserver 8000"

:: Esperar 3 segundos para que Django arranque
timeout /t 3 /nobreak >nul

:: ── Iniciar Streamlit en segundo plano ──
echo   >> Streamlit frontend en http://localhost:8082
start "Streamlit-Frontend" cmd /k "cd /d %~dp0\frontend && ..\venv\Scripts\activate && python -m streamlit run app.py --server.port 8082"

echo.
echo ============================================
echo   Servicios iniciados:
echo     - Backend:  http://127.0.0.1:8000
echo     - Frontend: http://localhost:8082
echo ============================================
echo.
echo Cierra las ventanas de Django y Streamlit para detener.
pause
