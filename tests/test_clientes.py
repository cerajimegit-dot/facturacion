"""Tests for Cliente CRUD with multi-tenant isolation."""
import pytest
from django.urls import reverse
from rest_framework import status
from apps.clientes.models import Cliente
from apps.empresas.models import Empresa
from apps.usuarios.models import Membership


@pytest.mark.django_db
class TestClienteCRUD:
    def test_crear_cliente(self, empresa_context):
        client, empresa = empresa_context
        url = reverse('cliente-list')
        data = {
            'nombre': 'Cliente Test',
            'ruc': '12345678-0',
            'telefono': '0981123456',
            'email': 'cliente@test.com',
            'tipo_cliente': 'persona',
        }
        response = client.post(f"{url}?empresa={empresa.id}", data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['nombre'] == 'Cliente Test'
        assert Cliente.objects.filter(empresa=empresa, ruc='12345678-0').exists()

    def test_listar_clientes_aislados_por_empresa(self, empresa_context, db):
        client, empresa = empresa_context
        # Create client in our empresa
        Cliente.objects.create(empresa=empresa, nombre='Nuestro', ruc='111-1')
        # Create client in another empresa
        otra = Empresa.objects.create(codigo='OTRA', nombre='Otra')
        Cliente.objects.create(empresa=otra, nombre='De Otra', ruc='222-2')

        url = reverse('cliente-list')
        response = client.get(f"{url}?empresa={empresa.id}")
        assert response.status_code == status.HTTP_200_OK
        nombres = [c['nombre'] for c in response.data['results']]
        assert 'Nuestro' in nombres
        assert 'De Otra' not in nombres

    def test_actualizar_cliente(self, empresa_context):
        client, empresa = empresa_context
        cliente = Cliente.objects.create(
            empresa=empresa, nombre='Original', ruc='333-3'
        )
        url = reverse('cliente-detail', kwargs={'pk': str(cliente.id)})
        response = client.patch(
            f"{url}?empresa={empresa.id}",
            {'nombre': 'Actualizado'},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['nombre'] == 'Actualizado'

    def test_eliminar_cliente(self, empresa_context):
        client, empresa = empresa_context
        cliente = Cliente.objects.create(
            empresa=empresa, nombre='A Eliminar', ruc='444-4'
        )
        url = reverse('cliente-detail', kwargs={'pk': str(cliente.id)})
        response = client.delete(f"{url}?empresa={empresa.id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Cliente.objects.filter(id=cliente.id).exists()

    def test_buscar_clientes(self, empresa_context):
        client, empresa = empresa_context
        Cliente.objects.create(empresa=empresa, nombre='Juan Perez', ruc='555-5')
        Cliente.objects.create(empresa=empresa, nombre='Maria Lopez', ruc='666-6')
        url = reverse('cliente-list')
        response = client.get(f"{url}?empresa={empresa.id}&search=Juan")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['nombre'] == 'Juan Perez'

    def test_sin_empresa_retorna_error(self, authenticated_client, membership):
        url = reverse('cliente-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
