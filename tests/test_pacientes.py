# tests/test_pacientes.py
"""
Pruebas para el módulo de pacientes
"""

import pytest
from datetime import date
from clinica.models import Paciente
from clinica import db


class TestPacientes:
    """Pruebas relacionadas con la gestión de pacientes"""
    
    def test_lista_pacientes_requires_auth(self, client):
        """Verifica que la lista de pacientes requiere autenticación"""
        response = client.get('/pacientes/', follow_redirects=False)
        # 308 es PERMANENT REDIRECT, también válido
        assert response.status_code in [302, 308]
    
    def test_lista_pacientes_loads(self, authenticated_client):
        """Verifica que la lista de pacientes carga para usuarios autenticados"""
        response = authenticated_client.get('/pacientes/', follow_redirects=True)
        assert response.status_code == 200
    
    def test_registrar_paciente_page_loads(self, authenticated_client):
        """Verifica que la página de registro de paciente carga"""
        response = authenticated_client.get('/pacientes/crear')
        assert response.status_code == 200
    
    def test_crear_paciente(self, authenticated_client, init_database, app):
        """Prueba la creación de un nuevo paciente"""
        with app.app_context():
            # Obtener el usuario autenticado para odontologo_id
            from clinica.models import Usuario
            usuario = Usuario.query.filter_by(username='testuser').first()
            
            # Datos del paciente
            data = {
                'nombres': 'Juan',
                'apellidos': 'Pérez',
                'tipo_documento': 'CC',
                'documento': '12345678',  # Cambiado de numero_documento a documento
                'fecha_nacimiento': '1990-01-01',
                'genero': 'Masculino',
                'telefono': '3001234567',
                'email': 'juan.perez@example.com',
                'direccion': 'Calle 123 #45-67',
                'estado_civil': 'Soltero',
                'odontologo_id': usuario.id
            }
            
            response = authenticated_client.post('/pacientes/crear', 
                                                data=data, 
                                                follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verificar que el paciente se creó en la base de datos
            paciente = Paciente.query.filter_by(documento='12345678').first()
            assert paciente is not None
            assert paciente.nombres == 'Juan'
            assert paciente.apellidos == 'Pérez'
    
    def test_buscar_paciente_ajax(self, authenticated_client, init_database, app):
        """Prueba la búsqueda de pacientes por AJAX"""
        with app.app_context():
            # Obtener el usuario para odontologo_id
            from clinica.models import Usuario
            usuario = Usuario.query.filter_by(username='testuser').first()
            
            # Crear un paciente de prueba
            paciente = Paciente(
                nombres='María',
                apellidos='González',
                tipo_documento='CC',
                documento='87654321',  # Cambiado de numero_documento a documento
                fecha_nacimiento=date(1985, 5, 15),
                genero='Femenino',
                telefono='3009876543',
                email='maria.gonzalez@example.com',
                odontologo_id=usuario.id
            )
            db.session.add(paciente)
            db.session.commit()
            
            # Buscar el paciente
            response = authenticated_client.get('/ajax/buscar_paciente?q=María')
            assert response.status_code == 200
            
            # Verificar que la respuesta es JSON
            json_data = response.get_json()
            assert json_data is not None
            assert len(json_data) > 0
            assert any('María' in str(p) for p in json_data)
    
    def test_editar_paciente_page_loads(self, authenticated_client, init_database, app):
        """Verifica que la página de edición de paciente carga"""
        with app.app_context():
            # Obtener el usuario para odontologo_id
            from clinica.models import Usuario
            usuario = Usuario.query.filter_by(username='testuser').first()
            
            # Crear un paciente de prueba
            paciente = Paciente(
                nombres='Pedro',
                apellidos='Ramírez',
                tipo_documento='CC',
                documento='11223344',  # Cambiado de numero_documento a documento
                fecha_nacimiento=date(1992, 3, 20),
                genero='Masculino',
                telefono='3001234567',
                odontologo_id=usuario.id
            )
            db.session.add(paciente)
            db.session.commit()
            paciente_id = paciente.id
        
        response = authenticated_client.get(f'/pacientes/{paciente_id}/editar')
        assert response.status_code == 200
    
    def test_editar_paciente_inexistente(self, authenticated_client):
        """Prueba editar un paciente que no existe"""
        response = authenticated_client.get('/pacientes/99999/editar')
        # Debe redirigir o mostrar error 404
        assert response.status_code in [302, 404]
