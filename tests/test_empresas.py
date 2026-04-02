"""Tests for Empresa CRUD and membership isolation."""
import pytest
from django.urls import reverse
from rest_framework import status
from apps.empresas.models import Empresa
from apps.usuarios.models import Membership


@pytest.mark.django_db
class TestEmpresaCRUD:
    def test_crear_empresa(self, authenticated_client, usuario):
        url = reverse('empresa-list')
        data = {
            'codigo': 'NEW001',
            'nombre': 'Nueva Empresa',
            'ruc': '80099999-0',
            'moneda_principal': 'PYG',
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['codigo'] == 'NEW001'
        # Should auto-create admin membership
        assert Membership.objects.filter(
            usuario=usuario, empresa__codigo='NEW001', rol='admin'
        ).exists()

    def test_listar_empresas_solo_propias(self, authenticated_client, empresa, membership):
        # Create another empresa the user does NOT belong to
        Empresa.objects.create(codigo='OTHER', nombre='Otra Empresa')
        url = reverse('empresa-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        codigos = [e['codigo'] for e in response.data['results']]
        assert 'EMP001' in codigos
        assert 'OTHER' not in codigos
        # Ensure list serializer exposes fields required by frontend
        empresa_data = next(e for e in response.data['results'] if e['codigo'] == 'EMP001')
        assert 'ruc' in empresa_data
        assert 'telefono' in empresa_data
        assert 'email' in empresa_data
        assert 'direccion' in empresa_data


    def test_detalle_empresa(self, authenticated_client, empresa, membership):
        url = reverse('empresa-detail', kwargs={'pk': str(empresa.id)})
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['codigo'] == empresa.codigo

    def test_actualizar_empresa(self, authenticated_client, empresa, membership):
        url = reverse('empresa-detail', kwargs={'pk': str(empresa.id)})
        response = authenticated_client.patch(url, {'nombre': 'Nombre Actualizado'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['nombre'] == 'Nombre Actualizado'

    def test_no_autenticado(self, api_client):
        url = reverse('empresa-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
