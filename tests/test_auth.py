"""Tests for authentication: registration, login, profile, password change."""
import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestRegistro:
    def test_registro_exitoso(self, api_client):
        url = reverse('registro')
        data = {
            'email': 'new@example.com',
            'first_name': 'Nuevo',
            'last_name': 'Usuario',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['email'] == 'new@example.com'
        assert response.data['username']  # auto-generated
        assert 'password' not in response.data

    def test_registro_passwords_no_coinciden(self, api_client):
        url = reverse('registro')
        data = {
            'email': 'new@example.com',
            'password': 'SecurePass123!',
            'password2': 'DifferentPass123!',
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_registro_password_debil(self, api_client):
        url = reverse('registro')
        data = {
            'email': 'new@example.com',
            'password': '123',
            'password2': '123',
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLogin:
    def test_login_exitoso(self, api_client, usuario):
        url = reverse('login')
        data = {'email': 'test@example.com', 'password': 'TestPass123!'}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert 'user' in response.data

    def test_login_credenciales_invalidas(self, api_client, usuario):
        url = reverse('login')
        data = {'email': 'test@example.com', 'password': 'WrongPass'}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_token_refresh(self, api_client, usuario):
        login_url = reverse('login')
        data = {'email': 'test@example.com', 'password': 'TestPass123!'}
        login_response = api_client.post(login_url, data)
        refresh_token = login_response.data['refresh']

        refresh_url = reverse('token_refresh')
        response = api_client.post(refresh_url, {'refresh': refresh_token})
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data


@pytest.mark.django_db
class TestPerfil:
    def test_obtener_perfil(self, authenticated_client, usuario):
        url = reverse('perfil')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == usuario.username

    def test_actualizar_perfil(self, authenticated_client):
        url = reverse('perfil')
        response = authenticated_client.patch(url, {'first_name': 'Updated'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['first_name'] == 'Updated'

    def test_perfil_no_autenticado(self, api_client):
        url = reverse('perfil')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestCambiarPassword:
    def test_cambiar_password_exitoso(self, authenticated_client):
        url = reverse('cambiar_password')
        data = {
            'old_password': 'TestPass123!',
            'new_password': 'NewSecurePass456!',
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK

    def test_cambiar_password_old_incorrecta(self, authenticated_client):
        url = reverse('cambiar_password')
        data = {
            'old_password': 'WrongOldPass',
            'new_password': 'NewSecurePass456!',
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
