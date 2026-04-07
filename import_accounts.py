#!/usr/bin/env python
import os
import sys
import django
import pandas as pd

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.contabilidad.models import PlanCuentas, TipoCuenta

excel_path = r'C:\Users\prueb\Downloads\ejemplo_plan.xlsx'

def import_accounts():
    if not os.path.exists(excel_path):
        print(f"❌ Archivo no encontrado: {excel_path}")
        return
    
    try:
        df = pd.read_excel(excel_path, sheet_name=0)
        print(f"✅ Leyendo {len(df)} cuentas del Excel...")
        
        # Mostrar primeras filas
        print("\nPrimeras cuentas:")
        print(df.head().to_string())
        
        # Crear tipos de cuenta si no existen
        tipos = {
            'Activa': TipoCuenta.objects.filter(nombre='Activa').first() or TipoCuenta.objects.create(nombre='Activa'),
            'Pasiva': TipoCuenta.objects.filter(nombre='Pasiva').first() or TipoCuenta.objects.create(nombre='Pasiva'),
            'Patrimonio': TipoCuenta.objects.filter(nombre='Patrimonio').first() or TipoCuenta.objects.create(nombre='Patrimonio'),
        }
        
        created = 0
        skipped = 0
        
        for _, row in df.iterrows():
            cod = str(row.get('codigo_cuenta', '')).strip()
            desc = str(row.get('descripcion', '')).strip()
            
            if not cod or not desc:
                continue
            
            # Determinar tipo
            if cod.startswith('1'):
                tipo = tipos['Activa']
            elif cod.startswith('2'):
                tipo = tipos['Pasiva']
            else:
                tipo = tipos['Patrimonio']
            
            # Crear si no existe
            if not PlanCuentas.objects.filter(codigo_cuenta=cod).exists():
                PlanCuentas.objects.create(
                    codigo_cuenta=cod,
                    descripcion=desc,
                    tipo_cuenta=tipo,
                    activo=True
                )
                created += 1
                print(f"  ✅ Creada: {cod} - {desc}")
            else:
                skipped += 1
        
        print(f"\n📊 Resumen:")
        print(f"  - Creadas: {created}")
        print(f"  - Omitidas (ya existen): {skipped}")
        print(f"  - Total en BD: {PlanCuentas.objects.count()}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    import_accounts()
