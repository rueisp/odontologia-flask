# tests/conftest.py
"""
Configuración de fixtures para pytest.
Los fixtures son funciones que se ejecutan antes de las pruebas
para preparar el entorno de prueba.
"""

import pytest
import os
import sys

# Agregar el directorio raíz al path para poder importar la app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from clinica import create_app, db
from clinica.models import Usuario, Paciente, Cita


@pytest.fixture(scope='session')
def app():
    """
    Crea una instancia de la aplicación para pruebas.
    scope='session' significa que se crea una sola vez para todas las pruebas.
    """
    # Configuración específica para pruebas
    os.environ['TESTING'] = '1'
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'  # Base de datos en memoria
    os.environ['SECRET_KEY'] = 'test-secret-key'
    
    app = create_app()
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,  # Desactivar CSRF para pruebas
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    })
    
    return app


@pytest.fixture(scope='function')
def client(app):
    """
    Crea un cliente de prueba para hacer peticiones HTTP.
    scope='function' significa que se crea uno nuevo para cada prueba.
    """
    return app.test_client()


@pytest.fixture(scope='function')
def init_database(app):
    """
    Inicializa la base de datos con tablas vacías para cada prueba.
    """
    with app.app_context():
        db.create_all()
        
        # Crear un usuario de prueba
        usuario_test = Usuario(
            username='testuser',
            email='test@example.com',
            is_admin=False
        )
        usuario_test.set_password('password123')
        db.session.add(usuario_test)
        
        # Crear un usuario administrador de prueba
        admin_test = Usuario(
            username='admin',
            email='admin@example.com',
            is_admin=True
        )
        admin_test.set_password('admin123')
        db.session.add(admin_test)
        
        db.session.commit()
        
        yield db  # Aquí se ejecutan las pruebas
        
        # Limpiar después de cada prueba
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def authenticated_client(client, init_database):
    """
    Cliente autenticado para pruebas que requieren login.
    """
    # Login con el usuario de prueba
    client.post('/login', data={
        'usuario': 'testuser',
        'contrasena': 'password123'
    }, follow_redirects=True)
    
    return client


@pytest.fixture(scope='function')
def admin_client(client, init_database):
    """
    Cliente autenticado como administrador.
    """
    # Login con el usuario administrador
    client.post('/login', data={
        'usuario': 'admin',
        'contrasena': 'admin123'
    }, follow_redirects=True)
    
    return client
