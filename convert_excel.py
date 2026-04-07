"""Script para convertir archivo Excel de .xls a .xlsx"""
import os
import sys

# Primero intentar instalar xlrd si no está disponible
try:
    import xlrd
except ImportError:
    print("Instalando xlrd...")
    os.system(f"{sys.executable} -m pip install xlrd -q")
    import xlrd

import openpyxl
from openpyxl.styles import Font, Alignment

# Rutas
ruta_xls = r"C:\Users\prueb\Downloads\ejemplo_plan.xls"
ruta_xlsx = r"C:\Users\prueb\Downloads\ejemplo_plan.xlsx"

print(f"Leyendo archivo: {ruta_xls}")

# Leer XLS
try:
    libro_xls = xlrd.open_workbook(ruta_xls)
    hoja_xls = libro_xls.sheet_by_index(0)
    
    # Crear XLSX
    libro_xlsx = openpyxl.Workbook()
    hoja_xlsx = libro_xlsx.active
    hoja_xlsx.title = "Plan de Cuentas"
    
    # Copiar datos
    for fila_idx in range(hoja_xls.nrows):
        for col_idx in range(hoja_xls.ncols):
            celda_valor = hoja_xls.cell_value(fila_idx, col_idx)
            hoja_xlsx.cell(row=fila_idx + 1, column=col_idx + 1, value=celda_valor)
    
    # Guardar
    libro_xlsx.save(ruta_xlsx)
    print(f"Archivo convertido exitosamente: {ruta_xlsx}")
    print(f"Total de filas: {hoja_xls.nrows}")
    print(f"Total de columnas: {hoja_xls.ncols}")
    
    # Mostrar primeras filas
    print("\nPrimeras 3 filas:")
    for fila_idx in range(min(3, hoja_xls.nrows)):
        fila = []
        for col_idx in range(hoja_xls.ncols):
            fila.append(str(hoja_xls.cell_value(fila_idx, col_idx)))
        print("  " + " | ".join(fila))
        
except Exception as e:
    print(f"Error: {str(e)}")
    sys.exit(1)
