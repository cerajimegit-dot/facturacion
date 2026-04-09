#!/usr/bin/env python
"""
Test registering clients from examples/clientes.xlsx using the API.
Uses the import endpoint to upload, validate, and import client data.
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime

os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
sys.stdout.reconfigure(encoding='utf-8')

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.empresas.models import Empresa
from apps.importacion.models import ImportJob
from apps.importacion.tasks import validate_import_task, execute_import_task
from apps.clientes.models import Cliente
from django.core.files import File
import logging

User = get_user_model()
logger = logging.getLogger('apps.importacion')

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

def main():
    print_header("PRUEBA DE IMPORTACIÓN - ARCHIVO CLIENTES.XLSX")
    print(f"Iniciada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # PASO 1: Obtener usuario
    print_step(1, "Obtener usuario para la importación")
    try:
        user, created = User.objects.get_or_create(
            email='import_test@test.com',
            defaults={'username': 'import_test', 'first_name': 'Import', 'last_name': 'Test'}
        )
        if created:
            user.set_password('Test123!@#')
            user.save()
            print_ok(f"Usuario creado: {user.email}")
        else:
            print_ok(f"Usuario encontrado: {user.email}")
    except Exception as e:
        print_err(f"Error con usuario: {e}")
        return

    # PASO 2: Obtener/crear empresa
    print_step(2, "Obtener/crear empresa")
    try:
        empresa, created = Empresa.objects.get_or_create(
            codigo='TEST_MAIN',
            defaults={'nombre': 'Empresa Principal Test', 'activa': True}
        )
        if created:
            print_ok(f"Empresa creada: {empresa.nombre}")
        else:
            print_ok(f"Empresa encontrada: {empresa.nombre}")
        empresa_id = str(empresa.id)
    except Exception as e:
        print_err(f"Error con empresa: {e}")
        return

    # PASO 3: Verificar archivo clientes.xlsx
    print_step(3, "Verificar archivo clientes.xlsx")
    excel_file = Path("examples/clientes.xlsx")
    if not excel_file.exists():
        print_err(f"Archivo no existe: {excel_file}")
        return
    
    file_size = excel_file.stat().st_size
    print_ok(f"Archivo encontrado: {excel_file}")
    print(f"   Tamaño: {file_size / 1024:.1f} KB")
    
    # Mostrar preview del contenido
    try:
        import pandas as pd
        df = pd.read_excel(excel_file)
        print(f"   Filas: {len(df)}")
        print(f"   Columnas: {list(df.columns)}")
        print(f"\n   Preview (primeras 3 filas):")
        print(df.head(3).to_string(index=False))
    except Exception as e:
        print_err(f"Error leyendo preview: {e}")

    # PASO 4: Crear ImportJob con el archivo
    print_step(4, "Crear ImportJob en base de datos")
    try:
        from django.core.files import File
        with open(excel_file, 'rb') as f:
            job = ImportJob.objects.create(
                empresa_id=empresa_id,
                usuario=user,
                archivo=File(f, name=excel_file.name),
                tipo='clientes',
                total_filas=len(df),
            )
        job_id = str(job.id)
        print_ok(f"ImportJob creado: {job_id}")
        print(f"   Estado: {job.estado}")
        print(f"   Total filas: {job.total_filas}")
    except Exception as e:
        print_err(f"Error creando ImportJob: {e}")
        import traceback
        traceback.print_exc()
        return

    # PASO 5: Ejecutar validación
    print_step(5, "Ejecutar validación de datos")
    try:
        print(f"   Llamando validate_import_task({job_id})")
        result = validate_import_task(job_id)
        
        job.refresh_from_db()
        print_ok(f"Validación completada")
        print(f"   Estado: {job.estado}")
        print(f"   Filas totales: {job.total_filas}")
        print(f"   Filas válidas: {job.filas_validas}")
        print(f"   Filas con errores: {job.filas_errores}")
        print(f"   Filas con warnings: {job.filas_warnings}")
        
        if job.estado != 'validado':
            print_err(f"Validación falló, estado: {job.estado}")
            if job.reporte_validacion:
                print(f"   Reporte: {job.reporte_validacion}")
            return
            
    except Exception as e:
        print_err(f"Error en validación: {e}")
        import traceback
        traceback.print_exc()
        return

    # PASO 6: Ejecutar importación
    print_step(6, "Ejecutar importación de clientes")
    try:
        clientes_antes = Cliente.objects.filter(empresa=empresa).count()
        print(f"   Clientes en BD antes: {clientes_antes}")
        
        print(f"   Llamando execute_import_task({job_id})")
        result = execute_import_task(job_id)
        
        job.refresh_from_db()
        clientes_despues = Cliente.objects.filter(empresa=empresa).count()
        
        print_ok(f"Importación completada")
        print(f"   Estado final: {job.estado}")
        print(f"   Filas importadas: {job.filas_importadas}")
        print(f"   Clientes antes: {clientes_antes}")
        print(f"   Clientes después: {clientes_despues}")
        print(f"   Clientes nuevos: {clientes_despues - clientes_antes}")
        
        if clientes_despues > clientes_antes:
            print_ok(f"✓✓✓ {clientes_despues - clientes_antes} CLIENTES REGISTRADOS EXITOSAMENTE ✓✓✓")
        else:
            print_err(f"No se registraron clientes")
            
    except Exception as e:
        print_err(f"Error en importación: {e}")
        import traceback
        traceback.print_exc()
        return

    # PASO 7: Mostrar clientes importados
    print_step(7, "Verificar clientes registrados en la base de datos")
    try:
        clientes_nuevos = Cliente.objects.filter(empresa=empresa).order_by('-created_at')[:10]
        
        if clientes_nuevos.count() > 0:
            print_ok(f"Clientes encontrados: {clientes_nuevos.count()}")
            for i, cliente in enumerate(clientes_nuevos, 1):
                print(f"   {i}. RUC: {cliente.ruc:15} | Nombre: {cliente.nombre:30} | Email: {cliente.email:25} | Tel: {cliente.telefono}")
        else:
            print_err(f"No se encontraron clientes")
            
    except Exception as e:
        print_err(f"Error verificando clientes: {e}")

    # PASO 8: Resumen de registros
    print_step(8, "Resumen de la importación")
    print_ok(f"Job ID: {job_id}")
    print_ok(f"Estado final: {job.estado}")
    print_ok(f"Tipo: {job.tipo}")
    print_ok(f"Filas procesadas: {job.total_filas}")
    print_ok(f"Filas importadas: {job.filas_importadas}")
    print_ok(f"Filas con errores: {job.filas_errores}")
    if job.filas_warnings:
        print(f"   Filas con advertencias: {job.filas_warnings}")

    print_header("PRUEBA COMPLETADA")
    print(f"Finalizada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

if __name__ == '__main__':
    main()
