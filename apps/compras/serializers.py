"""Serializers para compras y gastos."""
from decimal import Decimal
from rest_framework import serializers
from .models import Proveedor, Compra, CompraDetalle, Gasto, CategoriaGasto


class ProveedorSerializer(serializers.ModelSerializer):
    total_compras = serializers.IntegerField(read_only=True)
    cuenta_contable_desc = serializers.CharField(source='cuenta_contable.descripcion', read_only=True, allow_null=True)

    class Meta:
        model = Proveedor
        fields = [
            'id', 'nombre', 'ruc_numero', 'ruc_alfanumerico', 'pais', 'direccion',
            'telefono', 'email', 'email_set', 'contacto_nombre', 'activo',
            'importancia', 'dias_credito', 'notas',
            'emite_electronica', 'timbrado_numero', 'timbrado_vencimiento',
            'cuenta_contable', 'cuenta_contable_desc',
            'total_compras', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_compras', 'cuenta_contable_desc']


class ProveedorListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listas."""
    cuenta_contable_desc = serializers.CharField(source='cuenta_contable.descripcion', read_only=True, allow_null=True)
    
    class Meta:
        model = Proveedor
        fields = [
            'id', 'nombre', 'ruc_numero', 'ruc_alfanumerico', 'pais', 'email', 'email_set',
            'emite_electronica', 'timbrado_numero', 'activo',
            'cuenta_contable', 'cuenta_contable_desc'
        ]
        read_only_fields = ['cuenta_contable_desc']


class CategoriaGastoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaGasto
        fields = ['id', 'nombre', 'descripcion', 'activo']
        read_only_fields = ['id']


class CompraDetalleSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_sku = serializers.CharField(source='producto.sku', read_only=True)
    categoria_nombre = serializers.CharField(source='categoria_gasto.nombre', read_only=True)

    class Meta:
        model = CompraDetalle
        fields = [
            'id', 'compra', 'producto', 'producto_nombre', 'producto_sku',
            'es_servicio', 'categoria_gasto', 'categoria_nombre',
            'descripcion', 'cantidad', 'precio_unitario',
            'impuesto_porcentaje', 'subtotal', 'impuestos', 'total',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'subtotal', 'impuestos', 'total',
            'created_at', 'updated_at'
        ]


class CompraDetailedSerializer(serializers.ModelSerializer):
    """Serializer completo con detalles."""
    detalles = CompraDetalleSerializer(many=True, read_only=True)
    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True)
    almacen_nombre = serializers.CharField(source='almacen.nombre', read_only=True)
    usuario_registra_nombre = serializers.CharField(
        source='usuario_registra.get_full_name', read_only=True
    )
    usuario_recepcion_nombre = serializers.CharField(
        source='usuario_recepcion.get_full_name', read_only=True
    )
    puede_recibir = serializers.BooleanField(read_only=True)

    class Meta:
        model = Compra
        fields = [
            'id', 'numero', 'fecha', 'proveedor', 'proveedor_nombre',
            'almacen', 'almacen_nombre', 'moneda', 'cotizacion_usd',
            'detalles', 'subtotal', 'impuestos_total', 'total',
            'estado', 'puede_recibir',
            'usuario_registra', 'usuario_registra_nombre',
            'fecha_recepcion', 'usuario_recepcion', 'usuario_recepcion_nombre',
            'notas', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'subtotal', 'impuestos_total', 'total',
            'puede_recibir', 'fecha_recepcion', 'usuario_recepcion',
            'usuario_recepcion_nombre', 'created_at', 'updated_at'
        ]


class CompraListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listas."""
    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True)
    pais_proveedor = serializers.CharField(source='proveedor.pais', read_only=True)

    class Meta:
        model = Compra
        fields = [
            'id', 'numero', 'fecha', 'proveedor', 'proveedor_nombre',
            'pais_proveedor', 'moneda', 'total', 'estado', 'created_at'
        ]


class CompraSerializer(serializers.ModelSerializer):
    """Serializer para crear y actualizar compras con detalles."""
    detalles = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="Lista de items de la compra"
    )

    class Meta:
        model = Compra
        fields = [
            'id', 'numero', 'fecha', 'proveedor', 'almacen',
            'moneda', 'cotizacion_usd', 'notas', 'detalles',
            'subtotal', 'impuestos_total', 'total',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'subtotal', 'impuestos_total', 'total',
            'created_at', 'updated_at'
        ]

    def validate(self, data):
        """Validar que USD tenga cotización y que haya detalles."""
        if data.get('moneda') == 'USD' and not data.get('cotizacion_usd'):
            raise serializers.ValidationError({
                'cotizacion_usd': "La cotización USD es obligatoria cuando la moneda es USD"
            })
        
        detalles = data.get('detalles', [])
        if not detalles or len(detalles) == 0:
            raise serializers.ValidationError({
                'detalles': "Debe agregar al menos un item a la compra"
            })
        
        # Validar que cada detalle tenga datos requeridos
        for idx, detalle in enumerate(detalles):
            if not detalle.get('descripcion'):
                raise serializers.ValidationError({
                    'detalles': f"Item {idx + 1}: La descripción es obligatoria"
                })
            if not detalle.get('cantidad') or float(detalle.get('cantidad', 0)) <= 0:
                raise serializers.ValidationError({
                    'detalles': f"Item {idx + 1}: La cantidad debe ser mayor a 0"
                })
            if not detalle.get('precio_unitario') or float(detalle.get('precio_unitario', 0)) < 0:
                raise serializers.ValidationError({
                    'detalles': f"Item {idx + 1}: El precio debe ser válido"
                })
        
        return data

    def create(self, validated_data):
        """Crear compra con detalles y calcular totales."""
        detalles_data = validated_data.pop('detalles', [])
        
        # Obtener empresa del usuario (TenantModel required)
        request = self.context.get('request')
        empresa = request.user.empresa if request and hasattr(request, 'user') else None
        
        if not empresa:
            raise serializers.ValidationError({
                'empresa': 'No empresa found for user'
            })
        
        # Crear la compra con empresa
        validated_data['empresa'] = empresa
        compra = Compra.objects.create(**validated_data)
        
        # Crear detalles y calcular totales
        subtotal_total = Decimal('0')
        impuestos_total = Decimal('0')
        
        for detalle_data in detalles_data:
            cantidad = Decimal(str(detalle_data.get('cantidad', 0)))
            precio_unitario = Decimal(str(detalle_data.get('precio_unitario', 0)))
            impuesto_porcentaje = Decimal(str(detalle_data.get('impuesto_porcentaje', 0)))
            
            # Precio incluye IVA: total = qty * price, neto = total / (1 + iva%)
            total_item = cantidad * precio_unitario
            if impuesto_porcentaje > 0:
                divisor = Decimal('1') + (impuesto_porcentaje / Decimal('100'))
                subtotal_item = (total_item / divisor).quantize(Decimal('0.01'))
                impuestos_item = total_item - subtotal_item
            else:
                subtotal_item = total_item
                impuestos_item = Decimal('0')
            
            # Vincular producto si se envió producto_id
            producto = None
            producto_id = detalle_data.get('producto_id')
            if producto_id:
                from apps.productos.models import Producto
                try:
                    producto = Producto.objects.get(id=producto_id, empresa=empresa)
                except Producto.DoesNotExist:
                    pass
            
            CompraDetalle.objects.create(
                compra=compra,
                empresa=compra.empresa,
                producto=producto,
                descripcion=detalle_data.get('descripcion'),
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                impuesto_porcentaje=impuesto_porcentaje,
                es_servicio=producto is None,
            )
            
            # Acumular totales
            subtotal_total += subtotal_item
            impuestos_total += impuestos_item
        
        # Actualizar totales en la compra
        compra.subtotal = subtotal_total
        compra.impuestos_total = impuestos_total
        compra.total = subtotal_total + impuestos_total
        compra.save()
        
        return compra


class GastoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)

    class Meta:
        model = Gasto
        fields = [
            'id', 'fecha', 'categoria', 'categoria_nombre',
            'descripcion', 'monto', 'moneda', 'comprobante',
            'usuario', 'usuario_nombre', 'aprobado', 'notas',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'usuario', 'usuario_nombre', 'created_at', 'updated_at'
        ]
