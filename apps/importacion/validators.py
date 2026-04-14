"""Validation logic for Excel imports. Each entity has its own validator."""
import re
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime

logger = logging.getLogger('apps.importacion')

REQUIRED_COLUMNS = {
    'clientes': ['nombre', 'ruc'],
    'productos': ['sku', 'nombre', 'precio_unitario'],
    'stock': ['sku', 'almacen_codigo', 'cantidad'],
    'ventas': ['numero', 'fecha', 'cliente_ruc', 'sku', 'cantidad', 'precio_unitario'],
    'compras': ['numero', 'fecha', 'proveedor_ruc', 'proveedor_nombre', 'descripcion', 'cantidad', 'precio_unitario'],
    'activos_fijos': ['codigo', 'nombre', 'tipo', 'valor_adquisicion', 'vida_util_anios', 'fecha_adquisicion'],
}

OPTIONAL_COLUMNS = {
    'clientes': [
        'empresa_codigo', 'telefono', 'email', 'direccion_facturacion',
        'direccion_entrega', 'tipo_cliente', 'sector', 'zona', 'observaciones',
    ],
    'productos': [
        'empresa_codigo', 'descripcion', 'categoria', 'variante',
        'costo', 'imagen_url',
    ],
    'stock': ['empresa_codigo', 'ubicacion'],
    'ventas': [
        'empresa_codigo', 'impuestos', 'condicion_iva', 'estado', 'metodo_pago',
        'cliente_nombre', 'esta_pagada',
    ],
    'compras': [
        'proveedor_pais', 'proveedor_telefono', 'proveedor_email',
        'almacen_codigo', 'moneda', 'cotizacion_usd',
        'condicion_iva', 'sku', 'notas',
    ],
    'activos_fijos': [
        'descripcion', 'moneda', 'valor_residual',
        'clasificacion', 'ubicacion_planta', 'ubicacion_edificio', 'ubicacion_area',
        'centro_costo_codigo', 'centro_costo_descripcion',
        'numero_serie', 'numero_factura', 'propiedad_terceros',
    ],
}


def _is_blank(value):
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == '':
        return True
    return False


def _parse_decimal(value, field_name):
    """Try to parse a decimal value; return (Decimal, error_or_None)."""
    if _is_blank(value):
        return Decimal('0'), None
    try:
        d = Decimal(str(value).strip().replace(',', '.'))
        return d, None
    except (InvalidOperation, ValueError):
        return None, f"'{field_name}' no es un número válido: {value}"


def _parse_date(value, field_name):
    """Try to parse a date value; return (date, error_or_None)."""
    if _is_blank(value):
        return None, f"'{field_name}' es requerido"
    if isinstance(value, datetime):
        return value.date(), None
    val = str(value).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(val, fmt).date(), None
        except ValueError:
            continue
    return None, f"'{field_name}' formato de fecha inválido: {value}"


def _validate_email(value):
    if _is_blank(value):
        return True
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, str(value).strip()))


class ValidationResult:
    """Holds validation results for a single row."""
    def __init__(self, row_number):
        self.row_number = row_number
        self.errors = []
        self.warnings = []
        self.data = {}

    @property
    def is_valid(self):
        return len(self.errors) == 0

    @property
    def has_warnings(self):
        return len(self.warnings) > 0

    def to_dict(self):
        return {
            'fila': self.row_number,
            'valida': self.is_valid,
            'errores': self.errors,
            'warnings': self.warnings,
        }


def validate_clientes_row(row, row_num, existing_rucs=None):
    """Validate a single clientes row."""
    result = ValidationResult(row_num)
    existing_rucs = existing_rucs or set()

    # Required: nombre
    nombre = row.get('nombre')
    if _is_blank(nombre):
        result.errors.append("'nombre' es requerido")
    else:
        result.data['nombre'] = str(nombre).strip()

    # Required: ruc
    ruc = row.get('ruc')
    if _is_blank(ruc):
        result.errors.append("'ruc' es requerido")
    else:
        ruc_str = str(ruc).strip()
        result.data['ruc'] = ruc_str
        if ruc_str in existing_rucs:
            result.warnings.append(f"RUC duplicado: {ruc_str}")

    # Optional fields
    email = row.get('email')
    if not _is_blank(email) and not _validate_email(email):
        result.errors.append(f"'email' inválido: {email}")
    else:
        result.data['email'] = str(email).strip() if not _is_blank(email) else ''

    tipo = row.get('tipo_cliente', 'persona')
    if not _is_blank(tipo) and str(tipo).strip() not in ('persona', 'empresa'):
        result.warnings.append(f"'tipo_cliente' no reconocido: {tipo}, se usará 'persona'")
        result.data['tipo_cliente'] = 'persona'
    else:
        result.data['tipo_cliente'] = str(tipo).strip() if not _is_blank(tipo) else 'persona'

    for field in ['telefono', 'direccion_facturacion', 'direccion_entrega', 'sector', 'zona', 'observaciones']:
        val = row.get(field)
        result.data[field] = str(val).strip() if not _is_blank(val) else ''

    return result


def validate_productos_row(row, row_num, existing_skus=None):
    """Validate a single productos row."""
    result = ValidationResult(row_num)
    existing_skus = existing_skus or set()

    # Required: sku
    sku = row.get('sku')
    if _is_blank(sku):
        result.errors.append("'sku' es requerido")
    else:
        sku_str = str(sku).strip()
        result.data['sku'] = sku_str
        if sku_str in existing_skus:
            result.warnings.append(f"SKU duplicado: {sku_str}")

    # Required: nombre
    nombre = row.get('nombre')
    if _is_blank(nombre):
        result.errors.append("'nombre' es requerido")
    else:
        result.data['nombre'] = str(nombre).strip()

    # Required: precio_unitario
    precio, err = _parse_decimal(row.get('precio_unitario'), 'precio_unitario')
    if err:
        result.errors.append(err)
    elif precio is not None and precio < 0:
        result.errors.append("'precio_unitario' no puede ser negativo")
    else:
        result.data['precio_unitario'] = precio

    # Optional: costo
    costo, err = _parse_decimal(row.get('costo'), 'costo')
    if err:
        result.warnings.append(err)
        result.data['costo'] = Decimal('0')
    else:
        result.data['costo'] = costo or Decimal('0')

    for field in ['descripcion', 'categoria', 'variante', 'imagen_url']:
        val = row.get(field)
        result.data[field] = str(val).strip() if not _is_blank(val) else ''

    return result


def validate_stock_row(row, row_num, valid_skus=None, valid_almacenes=None):
    """Validate a single stock row."""
    result = ValidationResult(row_num)
    valid_skus = valid_skus or set()
    valid_almacenes = valid_almacenes or set()

    # Required: sku
    sku = row.get('sku')
    if _is_blank(sku):
        result.errors.append("'sku' es requerido")
    else:
        sku_str = str(sku).strip()
        result.data['sku'] = sku_str
        if valid_skus and sku_str not in valid_skus:
            result.errors.append(f"SKU no encontrado: {sku_str}")

    # Required: almacen_codigo
    almacen = row.get('almacen_codigo')
    if _is_blank(almacen):
        result.errors.append("'almacen_codigo' es requerido")
    else:
        alm_str = str(almacen).strip()
        result.data['almacen_codigo'] = alm_str
        if valid_almacenes and alm_str not in valid_almacenes:
            result.errors.append(f"Almacén no encontrado: {alm_str}")

    # Required: cantidad
    cantidad, err = _parse_decimal(row.get('cantidad'), 'cantidad')
    if err:
        result.errors.append(err)
    elif cantidad is not None and cantidad < 0:
        result.errors.append("'cantidad' no puede ser negativa")
    else:
        result.data['cantidad'] = cantidad

    ubicacion = row.get('ubicacion')
    result.data['ubicacion'] = str(ubicacion).strip() if not _is_blank(ubicacion) else ''

    return result


def validate_ventas_row(row, row_num, valid_rucs=None, valid_skus=None):
    """Validate a single ventas row."""
    result = ValidationResult(row_num)
    valid_rucs = valid_rucs or set()
    valid_skus = valid_skus or set()

    # Required: numero
    numero = row.get('numero')
    if _is_blank(numero):
        result.errors.append("'numero' es requerido")
    else:
        result.data['numero'] = str(numero).strip()

    # Required: fecha
    fecha, err = _parse_date(row.get('fecha'), 'fecha')
    if err:
        result.errors.append(err)
    else:
        result.data['fecha'] = fecha

    # Required: cliente_ruc
    cliente_ruc = row.get('cliente_ruc')
    if _is_blank(cliente_ruc):
        result.errors.append("'cliente_ruc' es requerido")
    else:
        ruc_str = str(cliente_ruc).strip()
        result.data['cliente_ruc'] = ruc_str
        if valid_rucs and ruc_str not in valid_rucs:
            result.errors.append(f"Cliente RUC no encontrado: {ruc_str}")

    # Required: sku
    sku = row.get('sku')
    if _is_blank(sku):
        result.errors.append("'sku' es requerido")
    else:
        sku_str = str(sku).strip()
        result.data['sku'] = sku_str
        if valid_skus and sku_str not in valid_skus:
            result.errors.append(f"SKU no encontrado: {sku_str}")

    # Required: cantidad
    cantidad, err = _parse_decimal(row.get('cantidad'), 'cantidad')
    if err:
        result.errors.append(err)
    elif cantidad is not None and cantidad <= 0:
        result.errors.append("'cantidad' debe ser mayor a 0")
    else:
        result.data['cantidad'] = cantidad

    # Required: precio_unitario
    precio, err = _parse_decimal(row.get('precio_unitario'), 'precio_unitario')
    if err:
        result.errors.append(err)
    elif precio is not None and precio < 0:
        result.errors.append("'precio_unitario' no puede ser negativo")
    else:
        result.data['precio_unitario'] = precio

    # Optional
    impuestos, err = _parse_decimal(row.get('impuestos', '10'), 'impuestos')
    if err:
        result.data['impuestos'] = Decimal('10')
    else:
        result.data['impuestos'] = impuestos

    estado = row.get('estado', 'confirmada')
    result.data['estado'] = str(estado).strip() if not _is_blank(estado) else 'confirmada'

    metodo = row.get('metodo_pago', '')
    result.data['metodo_pago'] = str(metodo).strip() if not _is_blank(metodo) else ''

    return result


def validate_compras_row(row, row_num, existing_proveedores=None):
    """Validate a single compras row."""
    result = ValidationResult(row_num)
    existing_proveedores = existing_proveedores or set()

    # Required: numero
    numero = row.get('numero')
    if _is_blank(numero):
        result.errors.append("'numero' es requerido")
    else:
        result.data['numero'] = str(numero).strip()

    # Required: fecha
    fecha, err = _parse_date(row.get('fecha'), 'fecha')
    if err:
        result.errors.append(err)
    else:
        result.data['fecha'] = fecha

    # Required: proveedor_ruc
    proveedor_ruc = row.get('proveedor_ruc')
    if _is_blank(proveedor_ruc):
        result.errors.append("'proveedor_ruc' es requerido")
    else:
        result.data['proveedor_ruc'] = str(proveedor_ruc).strip()

    # Required: proveedor_nombre
    proveedor_nombre = row.get('proveedor_nombre')
    if _is_blank(proveedor_nombre):
        result.errors.append("'proveedor_nombre' es requerido")
    else:
        result.data['proveedor_nombre'] = str(proveedor_nombre).strip()

    # Required: descripcion
    descripcion = row.get('descripcion')
    if _is_blank(descripcion):
        result.errors.append("'descripcion' es requerido")
    else:
        result.data['descripcion'] = str(descripcion).strip()

    # Required: cantidad
    cantidad, err = _parse_decimal(row.get('cantidad'), 'cantidad')
    if err:
        result.errors.append(err)
    elif cantidad is not None and cantidad <= 0:
        result.errors.append("'cantidad' debe ser mayor a 0")
    else:
        result.data['cantidad'] = cantidad

    # Required: precio_unitario
    precio, err = _parse_decimal(row.get('precio_unitario'), 'precio_unitario')
    if err:
        result.errors.append(err)
    elif precio is not None and precio < 0:
        result.errors.append("'precio_unitario' no puede ser negativo")
    else:
        result.data['precio_unitario'] = precio

    # Optional fields
    condicion = row.get('condicion_iva', 'gravada_10')
    cond_str = str(condicion).strip() if not _is_blank(condicion) else 'gravada_10'
    if cond_str not in ('gravada_10', 'gravada_5', 'exenta'):
        result.warnings.append(f"condicion_iva '{cond_str}' no reconocida, se usará 'gravada_10'")
        cond_str = 'gravada_10'
    result.data['condicion_iva'] = cond_str

    for field in ['proveedor_pais', 'proveedor_telefono', 'proveedor_email',
                   'almacen_codigo', 'moneda', 'sku', 'notas']:
        val = row.get(field)
        result.data[field] = str(val).strip() if not _is_blank(val) else ''

    cotiz, err = _parse_decimal(row.get('cotizacion_usd'), 'cotizacion_usd')
    result.data['cotizacion_usd'] = cotiz if cotiz else None

    return result


def validate_activos_fijos_row(row, row_num):
    """Validate a single activos_fijos row."""
    result = ValidationResult(row_num)

    # Required: codigo
    codigo = row.get('codigo')
    if _is_blank(codigo):
        result.errors.append("'codigo' es requerido")
    else:
        result.data['codigo'] = str(codigo).strip()

    # Required: nombre
    nombre = row.get('nombre')
    if _is_blank(nombre):
        result.errors.append("'nombre' es requerido")
    else:
        result.data['nombre'] = str(nombre).strip()

    # Required: tipo
    tipo = row.get('tipo')
    tipos_validos = ['it', 'planta', 'mobiliario', 'vehiculo', 'edificio', 'terreno', 'otro']
    if _is_blank(tipo):
        result.errors.append("'tipo' es requerido")
    else:
        tipo_str = str(tipo).strip().lower()
        if tipo_str not in tipos_validos:
            result.warnings.append(f"tipo '{tipo_str}' no estándar, se usará 'otro'")
            tipo_str = 'otro'
        result.data['tipo'] = tipo_str

    # Required: valor_adquisicion
    valor, err = _parse_decimal(row.get('valor_adquisicion'), 'valor_adquisicion')
    if err:
        result.errors.append(err)
    elif valor is not None and valor <= 0:
        result.errors.append("'valor_adquisicion' debe ser mayor a 0")
    else:
        result.data['valor_adquisicion'] = valor

    # Required: vida_util_anios
    vida, err = _parse_decimal(row.get('vida_util_anios'), 'vida_util_anios')
    if err:
        result.errors.append(err)
    elif vida is not None and vida <= 0:
        result.errors.append("'vida_util_anios' debe ser mayor a 0")
    else:
        result.data['vida_util_anios'] = int(vida) if vida else 5

    # Required: fecha_adquisicion
    fecha, err = _parse_date(row.get('fecha_adquisicion'), 'fecha_adquisicion')
    if err:
        result.errors.append(err)
    else:
        result.data['fecha_adquisicion'] = fecha

    # Optional: valor_residual
    residual, err = _parse_decimal(row.get('valor_residual', 0), 'valor_residual')
    result.data['valor_residual'] = residual if residual else Decimal('0')

    # Optional fields
    for field in ['descripcion', 'moneda', 'clasificacion',
                   'ubicacion_planta', 'ubicacion_edificio', 'ubicacion_area',
                   'centro_costo_codigo', 'centro_costo_descripcion',
                   'numero_serie', 'numero_factura']:
        val = row.get(field)
        result.data[field] = str(val).strip() if not _is_blank(val) else ''

    # propiedad_terceros (boolean)
    terceros = row.get('propiedad_terceros', False)
    if isinstance(terceros, bool):
        result.data['propiedad_terceros'] = terceros
    elif isinstance(terceros, str):
        result.data['propiedad_terceros'] = terceros.strip().lower() in ('si', 'sí', 'true', '1', 'yes')
    else:
        result.data['propiedad_terceros'] = bool(terceros)

    return result
