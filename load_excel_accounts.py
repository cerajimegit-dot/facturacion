import pandas as pd
import os

# Lee el archivo Excel
excel_path = r'C:\Users\prueb\Downloads\ejemplo_plan.xlsx'

if os.path.exists(excel_path):
    df = pd.read_excel(excel_path, sheet_name=0)
    print('Cuentas en el Excel:')
    print(df.to_string())
    print(f'\nTotal de cuentas: {len(df)}')
    print('\nCuentas pasivas (empiezan con 2):')
    passive = df[df['codigo_cuenta'].astype(str).str.startswith('2')]
    print(passive.to_string())
else:
    print(f"Archivo no encontrado: {excel_path}")
