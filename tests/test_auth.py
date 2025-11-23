# tests/test_auth.py
"""
Pruebas para autenticación (login, logout, registro)
"""

import pytest


class TestAuthentication:
    """Pruebas relacionadas con autenticación de usuarios"""
    
    def test_login_page_loads(self, client):
        """Verifica que la página de login carga correctamente"""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower() or b'iniciar' in response.data.lower()
    
    def test_login_with_valid_credentials(self, client, init_database):
        """Prueba login con credenciales válidas"""
        response = client.post('/login', data={
            'usuario': 'testuser',
            'contrasena': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Verificar que redirige al index después de login exitoso
        assert b'dashboard' in response.data.lower() or b'inicio' in response.data.lower()
    
    def test_login_with_invalid_password(self, client, init_database):
        """Prueba login con contraseña incorrecta"""
        response = client.post('/login', data={
            'usuario': 'testuser',
            'contrasena': 'wrongpassword'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'inv' in response.data.lower() or b'error' in response.data.lower()
    
    def test_login_with_nonexistent_user(self, client, init_database):
        """Prueba login con usuario que no existe"""
        response = client.post('/login', data={
            'usuario': 'noexiste',
            'contrasena': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'inv' in response.data.lower() or b'error' in response.data.lower()
    
    def test_logout(self, authenticated_client):
        """Prueba que el logout funciona correctamente"""
        response = authenticated_client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        
        # Intentar acceder a una ruta protegida después de logout
        response = authenticated_client.get('/')
        assert response.status_code == 302  # Debe redirigir a login
    
    def test_index_requires_authentication(self, client):
        """Verifica que el index requiere autenticación"""
        response = client.get('/')
        assert response.status_code == 302  # Redirección a login
        assert '/login' in response.location
    
    def test_registro_page_loads(self, client):
        """Verifica que la página de registro carga"""
        response = client.get('/registro')
        assert response.status_code == 200
    
    def test_registro_new_user(self, client, init_database):
        """Prueba registro de nuevo usuario"""
        response = client.post('/registro', data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpassword123',
            'confirm_password': 'newpassword123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Verificar que muestra mensaje de éxito o redirige a login
        assert b'exit' in response.data.lower() or b'login' in response.data.lower()
    
    def test_registro_duplicate_username(self, client, init_database):
        """Prueba registro con username duplicado"""
        response = client.post('/registro', data={
            'username': 'testuser',  # Ya existe
            'email': 'otro@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'uso' in response.data.lower() or b'existe' in response.data.lower()
    
    def test_registro_passwords_dont_match(self, client, init_database):
        """Prueba registro con contraseñas que no coinciden"""
        response = client.post('/registro', data={
            'username': 'newuser2',
            'email': 'newuser2@example.com',
            'password': 'password123',
            'confirm_password': 'differentpassword'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'coincid' in response.data.lower() or b'match' in response.data.lower()
