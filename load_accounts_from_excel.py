#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import pandas as pd
from apps.contabilidad.models import PlanCuentas

excel_path = r'C:\Users\prueb\Downloads\ejemplo_plan.xlsx'

if os.path.exists(excel_path):
    df = pd.read_excel(excel_path, sheet_name=0)
    print('✅ Cuentas en el Excel:')
    print(df[['codigo_cuenta', 'descripcion', 'tipo_cuenta']].to_string() if 'tipo_cuenta' in df.columns else df.to_string())
    
    print(f'\n📊 Total de cuentas: {len(df)}')
    
    # Contar por tipo
    if 'codigo_cuenta' in df.columns:
        activas = df[df['codigo_cuenta'].astype(str).str.startswith('1')]
        pasivas = df[df['codigo_cuenta'].astype(str).str.startswith('2')]
        print(f'  - Activas (1xxx): {len(activas)}')
        print(f'  - Pasivas (2xxx): {len(pasivas)}')
        
        print('\n💰 Cuentas pasivas (empiezan con 2):')
        print(pasivas[['codigo_cuenta', 'descripcion']].to_string() if 'descripcion' in pasivas.columns else pasivas.to_string())
        
        # Mostrar cuentas existentes en BD
        print(f'\n📈 Cuentas actuales en BD: {PlanCuentas.objects.count()}')
        existing = PlanCuentas.objects.values_list('codigo_cuenta', 'descripcion')
        for cod, desc in existing[:10]:
            print(f'  - {cod}: {desc}')
else:
    print(f"❌ Archivo no encontrado: {excel_path}")
