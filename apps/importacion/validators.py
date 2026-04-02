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
        'empresa_codigo', 'impuestos', 'estado', 'metodo_pago',
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
