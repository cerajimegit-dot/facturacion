"""Tests for presupuestos app."""
import logging
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.empresas.models import Empresa
from apps.usuarios.models import Membership
from apps.clientes.models import Cliente
from apps.productos.models import Producto, Categoria
from apps.presupuestos.models import Presupuesto, PresupuestoDetalle
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)
User = get_user_model()


class PresupuestoModelTest(TestCase):
    """Test Presupuesto model."""
    
    def setUp(self):
        """Set up test data."""
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create empresa
        self.empresa = Empresa.objects.create(
            nombre='Test Empresa',
            email='empresa@test.com'
        )
        
        # Add user to empresa
        Membership.objects.create(
            usuario=self.user,
            empresa=self.empresa,
            rol='admin',
            activo=True
        )
        
        # Create cliente
        self.cliente = Cliente.objects.create(
            nombre='Test Cliente',
            email='cliente@test.com',
            telefono='5951234567',
            empresa=self.empresa
        )
        
        # Create productos
        self.categoria = Categoria.objects.create(
            nombre='Test Category',
            empresa=self.empresa
        )
        
        self.producto1 = Producto.objects.create(
            sku='PROD-001',
            nombre='Producto 1',
            categoria=self.categoria,
            precio_unitario=100.00,
            empresa=self.empresa
        )
        
        self.producto2 = Producto.objects.create(
            sku='PROD-002',
            nombre='Producto 2',
            categoria=self.categoria,
            precio_unitario=200.00,
            empresa=self.empresa
        )
    
    def test_create_presupuesto(self):
        """Test creating a presupuesto."""
        presupuesto = Presupuesto.objects.create(
            numero='PRE-2024-001',
            empresa=self.empresa,
            cliente=self.cliente,
            email_cliente=self.cliente.email,
            telefono_cliente=self.cliente.telefono,
            creado_por=self.user
        )
        
        self.assertEqual(presupuesto.numero, 'PRE-2024-001')
        self.assertEqual(presupuesto.estado, 'borrador')
        self.assertEqual(presupuesto.empresa, self.empresa)
        logger.info(f"✓ Presupuesto creado: {presupuesto.numero}")
    
    def test_presupuesto_detail_calculation(self):
        """Test presupuesto detail calculations."""
        presupuesto = Presupuesto.objects.create(
            numero='PRE-2024-002',
            empresa=self.empresa,
            cliente=self.cliente,
            creado_por=self.user
        )
        
        # Add details
        detalle1 = PresupuestoDetalle.objects.create(
            presupuesto=presupuesto,
            producto=self.producto1,
            cantidad=5,
            precio_unitario=100.00,
            impuesto_porcentaje=19
        )
        
        detalle1.calcular_totales()
        
        # Verify calculations: 5 * 100 = 500, 500 * 0.19 = 95, total = 595
        self.assertEqual(detalle1.subtotal, 500.00)
        self.assertEqual(detalle1.total_impuesto, 95.00)
        self.assertEqual(detalle1.total, 595.00)
        
        logger.info(f"✓ Detalle calculado: subtotal={detalle1.subtotal}, "
                   f"impuesto={detalle1.total_impuesto}, total={detalle1.total}")
    
    def test_presupuesto_totals_calculation(self):
        """Test presupuesto total calculations."""
        presupuesto = Presupuesto.objects.create(
            numero='PRE-2024-003',
            empresa=self.empresa,
            cliente=self.cliente,
            creado_por=self.user
        )
        
        # Add multiple details
        detalle1 = PresupuestoDetalle.objects.create(
            presupuesto=presupuesto,
            producto=self.producto1,
            cantidad=5,
            precio_unitario=100.00,
            impuesto_porcentaje=19
        )
        
        detalle2 = PresupuestoDetalle.objects.create(
            presupuesto=presupuesto,
            producto=self.producto2,
            cantidad=3,
            precio_unitario=200.00,
            impuesto_porcentaje=19
        )
        
        detalle1.calcular_totales()
        detalle2.calcular_totales()
        
        # Calculate presupuesto totals
        presupuesto.calcular_totales()
        
        # Expected: (5*100 + 3*200) = 1100, impuesto = 209, total = 1309
        self.assertEqual(presupuesto.subtotal, 1100.00)
        self.assertEqual(presupuesto.total_impuesto, 209.00)
        self.assertEqual(presupuesto.total, 1309.00)
        
        logger.info(f"✓ Presupuesto calculado: subtotal={presupuesto.subtotal}, "
                   f"impuesto={presupuesto.total_impuesto}, total={presupuesto.total}")


class PresupuestoAPITest(TestCase):
    """Test Presupuesto API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create user
        self.user = User.objects.create_user(
            username='apiuser',
            email='api@example.com',
            password='testpass123'
        )
        
        # Create token
        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)
        
        # Create empresa
        self.empresa = Empresa.objects.create(
            nombre='API Test Empresa',
            email='api@empresa.com'
        )
        
        # Add user to empresa
        Membership.objects.create(
            usuario=self.user,
            empresa=self.empresa,
            rol='admin',
            activo=True
        )
        
        # Create cliente
        self.cliente = Cliente.objects.create(
            nombre='API Test Cliente',
            email='cliente@api.com',
            telefono='5951111111',
            empresa=self.empresa
        )
        
        # Set authorization
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
    
    def test_list_presupuestos(self):
        """Test listing presupuestos."""
        response = self.client.get('/api/v1/presupuestos/')
        self.assertEqual(response.status_code, 200)
        logger.info("✓ GET /api/v1/presupuestos/ - OK")
    
    def test_create_presupuesto_api(self):
        """Test creating presupuesto via API."""
        payload = {
            'cliente': self.cliente.id,
            'condiciones_pago': 'Pago al recibir',
            'detalles': [
                {
                    'descripcion': 'Test Product',
                    'cantidad': 1,
                    'precio_unitario': 100.00,
                    'impuesto_porcentaje': 19
                }
            ]
        }
        
        response = self.client.post(
            '/api/v1/presupuestos/',
            payload,
            format='json'
        )
        
        self.assertEqual(response.status_code, 201)
        self.assertIn('id', response.data)
        logger.info(f"✓ POST /api/v1/presupuestos/ - Created: {response.data.get('numero')}")
