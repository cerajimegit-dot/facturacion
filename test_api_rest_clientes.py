#!/usr/bin/env python
"""
Test the API REST endpoints for client import.
Tests HTTP requests to upload, validate, and import clients.
"""
import sys
import os
import requests
import json
import time
from pathlib import Path
from datetime import datetime

os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
sys.stdout.reconfigure(encoding='utf-8')

API_BASE = "http://127.0.0.1:8000/api/v1"
TOKEN = None
EMPRESA_ID = None

def print_header(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print('='*80)

def print_step(num, label):
    print(f"\n[PASO {num}] {label}")
    print("-" * 80)

def print_ok(msg):
    print(f"✓ {msg}")

def print_err(msg):
    print(f"✗ {msg}")

def print_response(resp, label=""):
    if label:
        print(f"   {label}")
    print(f"   HTTP {resp.status_code}")
    try:
        data = resp.json()
        print(f"   Response: {json.dumps(data, indent=2, default=str)[:500]}")
    except:
        print(f"   Response: {resp.text[:300]}")

def main():
    global TOKEN, EMPRESA_ID
    
    print_header("PRUEBA API REST - IMPORTACIÓN DE CLIENTES")
    print(f"Iniciada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # PASO 1: Login
    print_step(1, "Login en API")
    try:
        resp = requests.post(f"{API_BASE}/auth/login/", json={
            "email": "import_test@test.com",
            "password": "Test123!@#"
        }, timeout=5)
        
        if resp.status_code == 200:
            TOKEN = resp.json()["access"]
            print_ok(f"Login exitoso, token obtenido")
        else:
            print_err(f"Login falló: HTTP {resp.status_code}")
            print_response(resp)
            return
    except Exception as e:
        print_err(f"Error en login: {e}")
        return

    # PASO 2: Get empresas
    print_step(2, "Obtener empresas disponibles")
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    
    try:
        resp = requests.get(f"{API_BASE}/empresas/", headers=headers, timeout=5)
        
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and 'results' in data:
                empresas = data['results']
            else:
                empresas = data if isinstance(data, list) else []
            
            if empresas:
                EMPRESA_ID = empresas[0]['id']
                print_ok(f"Empresa encontrada: {empresas[0]['nombre']} (ID: {EMPRESA_ID})")
            else:
                print_err("No hay empresas disponibles")
                return
        else:
            print_err(f"Error: HTTP {resp.status_code}")
            print_response(resp)
            return
    except Exception as e:
        print_err(f"Error obteniendo empresas: {e}")
        return

    # PASO 3: Upload archivo
    print_step(3, "Hacer upload del archivo clientes.xlsx")
    excel_file = Path("examples/clientes.xlsx")
    
    if not excel_file.exists():
        print_err(f"Archivo no existe: {excel_file}")
        return
    
    try:
        with open(excel_file, 'rb') as f:
            files = {
                'archivo': (excel_file.name, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            }
            data = {
                'tipo': 'clientes',
                'empresa': EMPRESA_ID
            }
            
            resp = requests.post(
                f"{API_BASE}/importacion/upload/",
                headers={"Authorization": f"Bearer {TOKEN}"},
                files=files,
                data=data,
                timeout=10
            )
            
            print_response(resp, f"POST /importacion/upload/")
            
            if resp.status_code in [200, 201]:
                job_data = resp.json()
                job_id = job_data.get('id')
                print_ok(f"Upload exitoso")
                print(f"   Job ID: {job_id}")
                print(f"   Total filas: {job_data.get('total_filas')}")
                print(f"   Estado: {job_data.get('estado')}")
            else:
                print_err(f"Upload falló")
                return
    except Exception as e:
        print_err(f"Error en upload: {e}")
        return

    # PASO 4: Validar
    print_step(4, "Llamar endpoint de validación")
    
    try:
        resp = requests.post(
            f"{API_BASE}/importacion/{job_id}/validar/",
            headers=headers,
            timeout=10
        )
        
        print_response(resp, f"POST /importacion/{job_id}/validar/")
        
        if resp.status_code in [200, 201]:
            print_ok(f"Validación iniciada")
        else:
            print_err(f"Validación falló")
            return
    except Exception as e:
        print_err(f"Error en validación: {e}")
        return

    # Wait a bit for validation
    time.sleep(1)

    # PASO 5: Check status
    print_step(5, "Verificar estado de validación")
    
    try:
        resp = requests.get(
            f"{API_BASE}/importacion/{job_id}/",
            headers=headers,
            timeout=5
        )
        
        if resp.status_code == 200:
            job = resp.json()
            print_ok(f"Estado actual: {job.get('estado')}")
            print(f"   Filas válidas: {job.get('filas_validas')}")
            print(f"   Filas errores: {job.get('filas_errores')}")
            print(f"   Filas warnings: {job.get('filas_warnings')}")
            
            if job.get('estado') != 'validado':
                print_err(f"Validación incompleta, estado: {job.get('estado')}")
                return
        else:
            print_err(f"Error: HTTP {resp.status_code}")
            return
    except Exception as e:
        print_err(f"Error: {e}")
        return

    # PASO 6: Confirmar importación
    print_step(6, "Llamar endpoint de confirmación")
    
    try:
        resp = requests.post(
            f"{API_BASE}/importacion/{job_id}/confirmar/",
            headers=headers,
            timeout=10
        )
        
        print_response(resp, f"POST /importacion/{job_id}/confirmar/")
        
        if resp.status_code in [200, 201]:
            print_ok(f"Importación iniciada")
        else:
            print_err(f"Importación falló")
            return
    except Exception as e:
        print_err(f"Error en confirmación: {e}")
        return

    # Wait a bit for import
    time.sleep(1)

    # PASO 7: Check final status
    print_step(7, "Verificar estado final")
    
    try:
        resp = requests.get(
            f"{API_BASE}/importacion/{job_id}/",
            headers=headers,
            timeout=5
        )
        
        if resp.status_code == 200:
            job = resp.json()
            print_ok(f"Estado final: {job.get('estado')}")
            print(f"   Filas importadas: {job.get('filas_importadas')}")
            print(f"   Filas errores: {job.get('filas_errores')}")
            
            if job.get('estado') == 'completado':
                print_ok(f"✓✓✓ IMPORTACIÓN COMPLETADA EXITOSAMENTE ✓✓✓")
                print(f"   {job.get('filas_importadas')} clientes registrados")
            else:
                print_err(f"Importación incompleta")
        else:
            print_err(f"Error: HTTP {resp.status_code}")
            return
    except Exception as e:
        print_err(f"Error: {e}")
        return

    # PASO 8: Get clientes
    print_step(8, "Listar clientes importados")
    
    try:
        resp = requests.get(
            f"{API_BASE}/clientes/",
            headers=headers,
            params={"empresa": EMPRESA_ID},
            timeout=5
        )
        
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and 'results' in data:
                clientes = data['results']
            else:
                clientes = data if isinstance(data, list) else []
            
            print_ok(f"Clientes encontrados: {len(clientes)}")
            for i, cliente in enumerate(clientes[-5:], 1):  # Show last 5
                print(f"   {i}. {cliente.get('ruc')} - {cliente.get('nombre')} ({cliente.get('email')})")
        else:
            print_err(f"Error: HTTP {resp.status_code}")
    except Exception as e:
        print_err(f"Error: {e}")

    print_header("PRUEBA COMPLETADA")
    print(f"Finalizada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

if __name__ == '__main__':
    main()
