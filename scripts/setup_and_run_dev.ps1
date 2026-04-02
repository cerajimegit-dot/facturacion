<#
Script de ayuda: crear entorno virtual, instalar requisitos y levantar backend + frontend.
Uso: desde PowerShell en la raíz del proyecto, ejecutar:
    .\scripts\setup_and_run_dev.ps1
#>

param(
    [string]$venvPath = "venv",
    [string]$backendPort = "8000",
    [string]$frontendPort = "8501"
)

# 1. Ir al root del proyecto
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectDir = Resolve-Path "$scriptDir\.."
Set-Location $projectDir
Write-Host "Proyecto: $projectDir" -ForegroundColor Cyan

# 2. Crear y activar venv (si no existe)
if (-Not (Test-Path $venvPath)) {
    Write-Host "Creando entorno virtual en $venvPath..." -ForegroundColor Green
    python -m venv $venvPath
} else {
    Write-Host "Entorno virtual ya existe: $venvPath" -ForegroundColor Yellow
}

$activateScript = "$venvPath\Scripts\Activate.ps1"
if (-Not (Test-Path $activateScript)) {
    Write-Error "No se encontró el activate script en $activateScript"
    exit 1
}

Write-Host "Activando entorno virtual..." -ForegroundColor Green
. $activateScript

# 3. Instalar dependencias
Write-Host "Instalando requirements..." -ForegroundColor Green
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 4. Crear base de datos local si no existe
Write-Host "Creando la base de datos PostgreSQL si no existe..." -ForegroundColor Green
python scripts/create_postgres_db.py

# 5. Migraciones y preparativos
Write-Host "Ejecutando migraciones..." -ForegroundColor Green
python manage.py migrate --settings=config.settings

# 6. Iniciar backend y frontend en nuevas terminales
Write-Host "Iniciando backend en puerto $backendPort..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectDir'; python manage.py runserver 0.0.0.0:$backendPort" 

Write-Host "Iniciando frontend en puerto $frontendPort..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectDir\frontend'; streamlit run app.py --server.port $frontendPort --server.address 0.0.0.0"

Write-Host "Listo. Backend: http://127.0.0.1:$backendPort , Frontend: http://127.0.0.1:$frontendPort" -ForegroundColor Cyan
