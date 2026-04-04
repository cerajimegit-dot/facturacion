#!/usr/bin/env python
"""
Test import flow with detailed logging visibility.
Shows exactly where the import process fails.
"""
import sys
import os
import json
import time
from datetime import datetime

# Setup encoding
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
sys.stdout.reconfigure(encoding='utf-8')

import requests
import pandas as pd
from pathlib import Path

API = "http://127.0.0.1:8000/api/v1"

def print_section(title):
    """Print a section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)

def print_step(num, label):
    """Print a step number and label."""
    print(f"\n[PASO {num}] {label}")
    print("-" * 70)

def print_result(status, message, details=None):
    """Print result with status."""
    icon = "✓" if status else "✗"
    print(f"{icon} {message}")
    if details:
        print(f"   {details}")

def log_response(resp, show_body=True):
    """Log HTTP response."""
    print(f"   Status: HTTP {resp.status_code}")
    if show_body:
        try:
            body = resp.json()
            print(f"   Response: {json.dumps(body, indent=6, default=str)[:800]}")
        except:
            print(f"   Response: {resp.text[:400]}")
    return resp

def read_app_log():
    """Read the last lines of app.log."""
    log_file = Path("logs/app.log")
    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            return ''.join(lines[-20:])  # Last 20 lines
    return "Log file not found"

def main():
    print_section("PRUEBA DETALLADA DE IMPORTACIÓN")
    print(f"Iniciada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # PASO 1: Create test Excel file
    print_step(1, "Crear archivo Excel de prueba")
    excel_file = Path("test_import_sample.xlsx")
    
    try:
        # Create sample data
        data = {
            'cedula': ['1001', '1002', '1003'],
            'nombre': ['Cliente Test 1', 'Cliente Test 2', 'Cliente Test 3'],
            'email': ['c1@test.com', 'c2@test.com', 'c3@test.com'],
            'telefono': ['555-0001', '555-0002', '555-0003'],
            'direccion': ['Calle 1', 'Calle 2', 'Calle 3']
        }
        df = pd.DataFrame(data)
        df.to_excel(excel_file, index=False, sheet_name='clientes')
        print_result(True, f"Archivo creado: {excel_file}")
        print(f"   Filas: {len(df)}")
        print(f"   Columnas: {list(df.columns)}")
    except Exception as e:
        print_result(False, f"Error al crear archivo: {e}")
        return

    # PASO 2: Check API availability
    print_step(2, "Verificar disponibilidad del API")
    try:
        resp = requests.get(f"{API}/empresas/", timeout=5)
        if resp.status_code in [200, 401]:
            print_result(True, f"API disponible en {API}")
        else:
            print_result(False, f"API retornó HTTP {resp.status_code}")
            return
    except Exception as e:
        print_result(False, f"No se puede conectar al API: {e}")
        print_result(False, "Asegúrate de que Django está corriendo en puerto 8000")
        print("   Ejecuta: python manage.py runserver")
        return

    # PASO 3: Get or create test empresa
    print_step(3, "Obtener/crear empresa de prueba")
    try:
        resp = requests.get(f"{API}/empresas/?limit=1")
        log_response(resp, show_body=False)
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get('results') and len(data['results']) > 0:
                empresa = data['results'][0]
                empresa_id = empresa['id']
                print_result(True, f"Empresa encontrada: {empresa.get('nombre', empresa_id)}")
                print(f"   ID: {empresa_id}")
            else:
                print_result(False, "No hay empresas registradas")
                print_result(False, "Crea una empresa primero en el admin")
                return
        else:
            print_result(False, f"Error al obtener empresas: HTTP {resp.status_code}")
            log_response(resp)
            return
    except Exception as e:
        print_result(False, f"Error al conectar: {e}")
        return

    # PASO 4: Upload import file
    print_step(4, "Hacer upload del archivo de importación")
    
    try:
        with open(excel_file, 'rb') as f:
            files = {'archivo': f}
            params = {'empresa': empresa_id}
            
            print(f"   Enviando archivo a: {API}/importacion/upload/")
            print(f"   Parámetros: {params}")
            
            resp = requests.post(
                f"{API}/importacion/upload/",
                files=files,
                data=params,
                timeout=10
            )
            log_response(resp)
            
            if resp.status_code not in [200, 201]:
                print_result(False, f"Upload falló con HTTP {resp.status_code}")
                return
            
            job_data = resp.json()
            job_id = job_data.get('id')
            print_result(True, f"Upload completado")
            print(f"   Job ID: {job_id}")
            print(f"   Estado: {job_data.get('estado')}")
            print(f"   Total filas: {job_data.get('total_filas')}")
            
    except Exception as e:
        print_result(False, f"Error durante upload: {e}")
        return

    # Show app.log after upload
    print("\n[APP LOG - After Upload]")
    print(read_app_log())

    # PASO 5: Call validar endpoint
    print_step(5, "Llamar a endpoint de validación")
    
    try:
        print(f"   Enviando POST a: {API}/importacion/{job_id}/validar/")
        resp = requests.post(
            f"{API}/importacion/{job_id}/validar/",
            json={}
        )
        log_response(resp)
        
        if resp.status_code not in [200, 201]:
            print_result(False, f"Validación falló con HTTP {resp.status_code}")
        else:
            print_result(True, f"Validación completada")
            
    except Exception as e:
        print_result(False, f"Error durante validación: {e}")

    # Show app.log after validation
    print("\n[APP LOG - After Validación]")
    print(read_app_log())

    # PASO 6: Call confirmar endpoint
    print_step(6, "Llamar a endpoint de confirmación")
    
    try:
        print(f"   Enviando POST a: {API}/importacion/{job_id}/confirmar/")
        resp = requests.post(
            f"{API}/importacion/{job_id}/confirmar/",
            json={}
        )
        log_response(resp)
        
        if resp.status_code not in [200, 201]:
            print_result(False, f"Confirmación falló con HTTP {resp.status_code}")
        else:
            print_result(True, f"Confirmación completada")
            
    except Exception as e:
        print_result(False, f"Error durante confirmación: {e}")

    # Show app.log after confirm
    print("\n[APP LOG - After Confirmación]")
    print(read_app_log())

    # PASO 7: Get final job state
    print_step(7, "Obtener estado final del job")
    
    try:
        resp = requests.get(f"{API}/importacion/{job_id}/")
        log_response(resp)
        
        if resp.status_code == 200:
            job = resp.json()
            print_result(True, f"Estado final obtenido")
            print(f"   Estado: {job.get('estado')}")
            print(f"   Total filas: {job.get('total_filas')}")
            print(f"   Filas validadas: {job.get('filas_validadas')}")
            print(f"   Filas importadas: {job.get('filas_importadas')}")
            print(f"   Errores: {job.get('errores', '{}')}")
    except Exception as e:
        print_result(False, f"Error al obtener estado: {e}")

    # Show full app.log
    print_step(8, "Log del servidor (últimas líneas)")
    print(read_app_log())

    print_section("PRUEBA COMPLETADA")
    print(f"Finalizada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    main()
