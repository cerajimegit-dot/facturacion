"""
Genera plantillas Excel limpias con encabezados + filas de ejemplo
para que los usuarios las completen y suban al sistema.
"""
import os
import sys

try:
    import pandas as pd
except ImportError:
    print("Instalar pandas: pip install pandas openpyxl")
    sys.exit(1)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'plantillas')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def gen_clientes():
    return pd.DataFrame([
        {'nombre': 'Distribuidora ABC S.A.', 'ruc': '80045678-3', 'telefono': '0981555111', 'email': 'abc@ejemplo.com', 'direccion_facturacion': 'Av. España 1234, Asunción', 'tipo_cliente': 'empresa', 'sector': 'Comercio', 'zona': 'Capital'},
        {'nombre': 'Juan Pérez', 'ruc': '4839399-1', 'telefono': '0971222333', 'email': 'jperez@gmail.com', 'direccion_facturacion': 'Calle 14 de Mayo 567', 'tipo_cliente': 'persona', 'sector': '', 'zona': 'Central'},
    ])


def gen_productos():
    return pd.DataFrame([
        {'sku': 'PROD-001', 'nombre': 'Cemento Portland 50kg', 'descripcion': 'Cemento gris uso general', 'categoria': 'Construcción', 'precio_unitario': 55000, 'costo': 42000},
        {'sku': 'PROD-002', 'nombre': 'Hierro 8mm x 12m', 'descripcion': 'Barra de hierro corrugado', 'categoria': 'Construcción', 'precio_unitario': 38000, 'costo': 28000},
        {'sku': 'SERV-001', 'nombre': 'Flete local', 'descripcion': 'Servicio de entrega zona capital', 'categoria': 'Servicios', 'precio_unitario': 150000, 'costo': 80000},
    ])


def gen_stock():
    return pd.DataFrame([
        {'sku': 'PROD-001', 'almacen_codigo': 'ALM01', 'cantidad': 500, 'ubicacion': 'A-01'},
        {'sku': 'PROD-002', 'almacen_codigo': 'ALM01', 'cantidad': 200, 'ubicacion': 'A-02'},
    ])


def gen_ventas():
    return pd.DataFrame([
        {'numero': '001-001-0000001', 'fecha': '2026-01-15', 'cliente_ruc': '80045678-3', 'cliente_nombre': 'Distribuidora ABC S.A.', 'descripcion': 'Cemento Portland 50kg', 'cantidad': 10, 'precio_unitario': 55000, 'condicion_iva': 'gravada_10', 'moneda': 'PYG', 'estado': 'confirmada', 'notas': 'Pedido #101'},
        {'numero': '001-001-0000001', 'fecha': '2026-01-15', 'cliente_ruc': '80045678-3', 'cliente_nombre': 'Distribuidora ABC S.A.', 'descripcion': 'Hierro 8mm x 12m', 'cantidad': 20, 'precio_unitario': 38000, 'condicion_iva': 'gravada_10', 'moneda': 'PYG', 'estado': 'confirmada', 'notas': 'Pedido #101'},
        {'numero': '001-001-0000002', 'fecha': '2026-01-20', 'cliente_ruc': '4839399-1', 'cliente_nombre': 'Juan Pérez', 'descripcion': 'Cemento Portland 50kg', 'cantidad': 5, 'precio_unitario': 55000, 'condicion_iva': 'gravada_10', 'moneda': 'PYG', 'estado': 'pagada', 'metodo_pago': 'efectivo', 'notas': ''},
        {'numero': '001-001-0000002', 'fecha': '2026-01-20', 'cliente_ruc': '4839399-1', 'cliente_nombre': 'Juan Pérez', 'descripcion': 'Flete local', 'cantidad': 1, 'precio_unitario': 150000, 'condicion_iva': 'exenta', 'moneda': 'PYG', 'estado': 'pagada', 'metodo_pago': 'efectivo', 'notas': ''},
    ])


def gen_compras():
    return pd.DataFrame([
        {'numero': 'FC-00123', 'fecha': '2026-01-10', 'proveedor_ruc': '80099887-5', 'proveedor_nombre': 'Cementos INC S.A.', 'descripcion': 'Cemento Portland 50kg', 'cantidad': 100, 'precio_unitario': 42000, 'condicion_iva': 'gravada_10', 'almacen_codigo': 'ALM01', 'moneda': 'PYG', 'notas': 'OC #50'},
        {'numero': 'FC-00123', 'fecha': '2026-01-10', 'proveedor_ruc': '80099887-5', 'proveedor_nombre': 'Cementos INC S.A.', 'descripcion': 'Hierro 8mm x 12m', 'cantidad': 50, 'precio_unitario': 28000, 'condicion_iva': 'gravada_10', 'almacen_codigo': 'ALM01', 'moneda': 'PYG', 'notas': 'OC #50'},
        {'numero': 'FC-00456', 'fecha': '2026-01-18', 'proveedor_ruc': '80011223-0', 'proveedor_nombre': 'Ferretería del Este', 'descripcion': 'Clavos 2 pulgadas x kg', 'cantidad': 30, 'precio_unitario': 15000, 'condicion_iva': 'gravada_5', 'almacen_codigo': 'ALM01', 'moneda': 'PYG', 'notas': ''},
    ])


def gen_activos_fijos():
    return pd.DataFrame([
        {'codigo': 'AF-001', 'nombre': 'Laptop Dell Latitude 5540', 'tipo': 'IT', 'descripcion': 'Laptop administración', 'valor_adquisicion': 15000000, 'valor_residual': 1500000, 'vida_util_anios': 5, 'fecha_adquisicion': '2025-01-15', 'moneda': 'PYG', 'clasificacion': 'Equipos IT', 'ubicacion_planta': 'Central', 'ubicacion_edificio': 'Oficina', 'ubicacion_area': 'Piso 1', 'centro_costo_codigo': 'CC-ADM', 'centro_costo_descripcion': 'Administración', 'numero_serie': 'SN-2025-001', 'numero_factura': 'FC-00789', 'propiedad_terceros': 'NO'},
        {'codigo': 'AF-002', 'nombre': 'Camioneta Toyota Hilux 2024', 'tipo': 'vehiculo', 'descripcion': 'Vehículo para entregas', 'valor_adquisicion': 180000000, 'valor_residual': 45000000, 'vida_util_anios': 8, 'fecha_adquisicion': '2024-06-01', 'moneda': 'PYG', 'clasificacion': 'Vehículos', 'ubicacion_planta': 'Central', 'ubicacion_edificio': 'Estacionamiento', 'ubicacion_area': '', 'centro_costo_codigo': 'CC-LOG', 'centro_costo_descripcion': 'Logística', 'numero_serie': 'VIN-ABC123456', 'numero_factura': 'FC-00550', 'propiedad_terceros': 'NO'},
        {'codigo': 'AF-003', 'nombre': 'Escritorio ejecutivo', 'tipo': 'mobiliario', 'descripcion': 'Escritorio madera oficina gerencia', 'valor_adquisicion': 3500000, 'valor_residual': 350000, 'vida_util_anios': 10, 'fecha_adquisicion': '2025-03-10', 'moneda': 'PYG', 'clasificacion': 'Mobiliario', 'ubicacion_planta': 'Central', 'ubicacion_edificio': 'Oficina', 'ubicacion_area': 'Piso 2', 'centro_costo_codigo': 'CC-ADM', 'centro_costo_descripcion': 'Administración', 'numero_serie': '', 'numero_factura': 'FC-00830', 'propiedad_terceros': 'NO'},
    ])


def main():
    print("Generando plantillas Excel para usuarios...\n")

    sheets = {
        'clientes': gen_clientes(),
        'productos': gen_productos(),
        'stock': gen_stock(),
        'ventas': gen_ventas(),
        'compras': gen_compras(),
        'activos_fijos': gen_activos_fijos(),
    }

    # Individual files
    for name, df in sheets.items():
        path = os.path.join(OUTPUT_DIR, f'plantilla_{name}.xlsx')
        df.to_excel(path, index=False, sheet_name=name)
        print(f"  plantilla_{name}.xlsx  ({len(df)} filas ejemplo, {len(df.columns)} columnas)")

    # Combined workbook
    combined = os.path.join(OUTPUT_DIR, 'plantilla_completa.xlsx')
    with pd.ExcelWriter(combined, engine='openpyxl') as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    print(f"  plantilla_completa.xlsx  (6 hojas combinadas)")

    print(f"\n✅ Plantillas generadas en: {OUTPUT_DIR}")
    print("\nInstrucciones para los usuarios:")
    print("  1. Abrir la plantilla correspondiente al tipo de datos")
    print("  2. Llenar las filas bajo los encabezados (pueden borrar las filas de ejemplo)")
    print("  3. NO cambiar los nombres de las columnas (encabezados)")
    print("  4. Guardar como .xlsx")
    print("  5. Subir en el sistema → Importación desde Excel")


if __name__ == '__main__':
    main()
