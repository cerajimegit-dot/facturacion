"""Shared pytest fixtures for all tests."""
import pytest
from apps.usuarios.models import Usuario, Membership
from apps.empresas.models import Empresa


@pytest.fixture
def usuario(db):
    """Create a test user."""
    user = Usuario.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='TestPass123!',
        first_name='Test',
        last_name='User',
    )
    return user


@pytest.fixture
def empresa(db):
    """Create a test empresa."""
    return Empresa.objects.create(
        codigo='EMP001',
        nombre='Empresa Test',
        ruc='80012345-6',
        razon_social='Empresa Test S.A.',
        moneda_principal='PYG',
    )


@pytest.fixture
def membership(usuario, empresa):
    """Create admin membership linking user to empresa."""
    return Membership.objects.create(
        usuario=usuario,
        empresa=empresa,
        rol='admin',
    )


@pytest.fixture
def api_client():
    """Return a DRF API client."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, usuario):
    """Return an authenticated API client."""
    api_client.force_authenticate(user=usuario)
    return api_client


@pytest.fixture
def empresa_context(authenticated_client, membership):
    """Return authenticated client with empresa membership set up."""
    return authenticated_client, membership.empresa
