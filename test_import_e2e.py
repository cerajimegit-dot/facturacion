#!/usr/bin/env python
"""
End-to-end test that actually imports data into the database.
Tests the complete flow without needing external API calls.
"""
import os
import sys
import django
import pandas as pd
from pathlib import Path
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.stdout.reconfigure(encoding='utf-8')
django.setup()

from django.contrib.auth import get_user_model
from apps.empresas.models import Empresa
from apps.importacion.models import ImportJob
from apps.importacion.tasks import validate_import_task, execute_import_task
from apps.clientes.models import Cliente
import logging

User = get_user_model()
logger = logging.getLogger('apps.importacion')

def print_header(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)

def print_step(num, label):
    print(f"\n[PASO {num}] {label}")
    print("-" * 70)

def print_ok(msg):
    print(f"✓ {msg}")

def print_err(msg):
    print(f"✗ {msg}")

def main():
    print_header("PRUEBA END-TO-END DE IMPORTACIÓN")
    print(f"Iniciada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # PASO 1: Crear/obtener usuario
    print_step(1, "Crear/obtener usuario de prueba")
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
            print_ok(f"Usuario existente: {user.email}")
    except Exception as e:
        print_err(f"Error creando usuario: {e}")
        return

    # PASO 2: Crear/obtener empresa
    print_step(2, "Crear/obtener empresa de prueba")
    try:
        empresa, created = Empresa.objects.get_or_create(
            codigo='TEST_IMP',
            defaults={'nombre': 'Empresa Test Importación', 'activa': True}
        )
        if created:
            print_ok(f"Empresa creada: {empresa.nombre}")
        else:
            print_ok(f"Empresa existente: {empresa.nombre}")
        empresa_id = str(empresa.id)
    except Exception as e:
        print_err(f"Error creando empresa: {e}")
        return

    # PASO 3: Crear archivo Excel de prueba
    print_step(3, "Crear archivo Excel de prueba")
    import time
    unique = str(int(time.time()))[-5:]  # Use timestamp for uniqueness
    excel_file = Path(f"test_import_e2e_{unique}.xlsx")
    try:
        data = {
            'cedula': [f'99{unique}01', f'99{unique}02', f'99{unique}03'],
            'ruc': [f'RUC{unique}01', f'RUC{unique}02', f'RUC{unique}03'],
            'nombre': ['Cliente E2E Test 1', 'Cliente E2E Test 2', 'Cliente E2E Test 3'],
            'email': [f'e2e{unique}1@test.com', f'e2e{unique}2@test.com', f'e2e{unique}3@test.com'],
            'telefono': ['555-9999', '555-9998', '555-9997'],
            'direccion': ['Calle Test 1', 'Calle Test 2', 'Calle Test 3']
        }
        df = pd.DataFrame(data)
        df.to_excel(excel_file, index=False, sheet_name='clientes')
        print_ok(f"Archivo creado: {excel_file}")
        print(f"   Filas: {len(df)}")
    except Exception as e:
        print_err(f"Error creando archivo: {e}")
        return

    # PASO 4: Crear ImportJob
    print_step(4, "Crear ImportJob en base de datos")
    try:
        from django.core.files import File
        with open(excel_file, 'rb') as f:
            job = ImportJob.objects.create(
                empresa_id=empresa_id,
                usuario=user,
                archivo=File(f, name=excel_file.name),
                tipo='clientes',
                total_filas=3,
            )
        job_id = str(job.id)
        print_ok(f"ImportJob creado: {job_id}")
        print(f"   Estado: {job.estado}")
        print(f"   Total filas: {job.total_filas}")
    except Exception as e:
        print_err(f"Error creando ImportJob: {e}")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
        return

    # PASO 5: Ejecutar validación
    print_step(5, "Ejecutar validación (validate_import_task)")
    try:
        print(f"   Calling validate_import_task({job_id})")
        result = validate_import_task(job_id)
        
        # Refresh job from DB
        job.refresh_from_db()
        print_ok(f"Validación completada")
        print(f"   Estado: {job.estado}")
        print(f"   Filas válidas: {job.filas_validas}/{job.total_filas}")
        print(f"   Filas con errores: {job.filas_errores}")
        print(f"   Filas con warnings: {job.filas_warnings}")
        
        if job.estado != 'validado':
            print_err(f"Job no llegó a estado 'validado', estado actual: {job.estado}")
            return
            
    except Exception as e:
        print_err(f"Error en validación: {e}")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
        return

    # PASO 6: Ejecutar importación
    print_step(6, "Ejecutar importación (execute_import_task)")
    try:
        # Count clientes antes
        clientes_antes = Cliente.objects.filter(empresa=empresa).count()
        print(f"   Clientes antes: {clientes_antes}")
        
        print(f"   Calling execute_import_task({job_id})")
        result = execute_import_task(job_id)
        
        # Refresh job from DB
        job.refresh_from_db()
        clientes_despues = Cliente.objects.filter(empresa=empresa).count()
        
        print_ok(f"Importación completada")
        print(f"   Estado: {job.estado}")
        print(f"   Filas importadas: {job.filas_importadas}")
        print(f"   Clientes antes: {clientes_antes}")
        print(f"   Clientes después: {clientes_despues}")
        print(f"   Clientes nuevos: {clientes_despues - clientes_antes}")
        
        if clientes_despues > clientes_antes:
            print_ok(f"✓✓✓ DATOS IMPORTADOS EXITOSAMENTE ✓✓✓")
        else:
            print_err(f"No se importaron clientes")
            
    except Exception as e:
        print_err(f"Error en importación: {e}")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
        return

    # PASO 7: Verificar datos
    print_step(7, "Verificar datos importados en base de datos")
    try:
        clientes_nuevos = Cliente.objects.filter(
            empresa=empresa,
            ruc__startswith='RUC'
        ).order_by('-created_at')[:3]
        
        if clientes_nuevos.count() > 0:
            print_ok(f"Clientes encontrados: {clientes_nuevos.count()}")
            for cliente in clientes_nuevos:
                print(f"   - {cliente.ruc}: {cliente.nombre} ({cliente.email})")
        else:
            print_err(f"No se encontraron clientes importados")
            
    except Exception as e:
        print_err(f"Error verificando datos: {e}")

    # PASO 8: Ver logs
    print_step(8, "Logs del servidor (últimas líneas)")
    log_file = Path("logs/app.log")
    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            # Show last 30 lines related to import
            import_lines = [l for l in lines if 'import' in l.lower() or 'validat' in l.lower()]
            if import_lines:
                print("Logs de importación:")
                for line in import_lines[-15:]:
                    print(f"  {line.rstrip()}")

    print_header("PRUEBA COMPLETADA")
    print(f"Finalizada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

if __name__ == '__main__':
    main()
