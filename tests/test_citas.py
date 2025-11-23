# tests/test_citas.py
"""
Pruebas para el módulo de citas
"""

import pytest
from datetime import datetime, timedelta, date
from clinica.models import Paciente, Cita
from clinica import db


class TestCitas:
    """Pruebas relacionadas con la gestión de citas"""
    
    def test_calendario_requires_auth(self, client):
        """Verifica que el calendario requiere autenticación"""
        response = client.get('/calendario/', follow_redirects=False)
        # 308 es PERMANENT REDIRECT, también válido
        assert response.status_code in [302, 308]
    
    def test_calendario_loads(self, authenticated_client):
        """Verifica que el calendario carga para usuarios autenticados"""
        response = authenticated_client.get('/calendario/', follow_redirects=True)
        assert response.status_code == 200
    
    def test_crear_cita(self, authenticated_client, init_database, app):
        """Prueba la creación de una nueva cita"""
        with app.app_context():
            # Obtener el usuario para odontologo_id
            from clinica.models import Usuario
            usuario = Usuario.query.filter_by(username='testuser').first()
            
            # Crear un paciente primero
            paciente = Paciente(
                nombres='Ana',
                apellidos='Martínez',
                tipo_documento='CC',
                documento='55667788',  # Cambiado de numero_documento a documento
                fecha_nacimiento=date(1988, 7, 10),
                genero='Femenino',
                telefono='3001234567',
                odontologo_id=usuario.id
            )
            db.session.add(paciente)
            db.session.commit()
            paciente_id = paciente.id
            
            # Crear una cita
            fecha_cita = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            data = {
                'paciente_id': paciente_id,
                'fecha': fecha_cita,
                'hora': '10:00',
                'motivo': 'Consulta general',
                'estado': 'pendiente',
                'doctor': 'Dr. Test'
            }
            
            response = authenticated_client.post('/calendario/cita/crear',
                                                data=data,
                                                follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verificar que la cita se creó
            cita = Cita.query.filter_by(paciente_id=paciente_id).first()
            assert cita is not None
            assert cita.motivo == 'Consulta general'
    
    def test_actualizar_estado_cita(self, authenticated_client, init_database, app):
        """Prueba actualizar el estado de una cita"""
        with app.app_context():
            # Obtener el usuario para odontologo_id
            from clinica.models import Usuario
            usuario = Usuario.query.filter_by(username='testuser').first()
            
            # Crear paciente y cita
            paciente = Paciente(
                nombres='Carlos',
                apellidos='López',
                tipo_documento='CC',
                documento='99887766',  # Cambiado de numero_documento a documento
                fecha_nacimiento=date(1995, 12, 5),
                genero='Masculino',
                telefono='3001234567',
                odontologo_id=usuario.id
            )
            db.session.add(paciente)
            db.session.commit()
            
            cita = Cita(
                paciente_id=paciente.id,
                fecha=datetime.now().date(),
                hora=datetime.now().time(),
                motivo='Control',
                estado='pendiente',
                doctor='Dr. Test'
            )
            db.session.add(cita)
            db.session.commit()
            cita_id = cita.id
        
        # Actualizar estado a completada
        response = authenticated_client.post(
            f'/calendario/cita/actualizar_estado/{cita_id}',
            json={'estado': 'completada'},
            content_type='application/json'
        )
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data is not None
        assert json_data.get('success') is True
        
        # Verificar en la base de datos
        with app.app_context():
            cita = Cita.query.get(cita_id)
            assert cita.estado == 'completada'
    
    def test_listar_citas_paciente(self, authenticated_client, init_database, app):
        """Prueba listar las citas de un paciente específico"""
        with app.app_context():
            # Obtener el usuario para odontologo_id
            from clinica.models import Usuario
            usuario = Usuario.query.filter_by(username='testuser').first()
            
            # Crear paciente
            paciente = Paciente(
                nombres='Laura',
                apellidos='Fernández',
                tipo_documento='CC',
                documento='44556677',  # Cambiado de numero_documento a documento
                fecha_nacimiento=date(1993, 4, 25),
                genero='Femenino',
                telefono='3001234567',
                odontologo_id=usuario.id
            )
            db.session.add(paciente)
            db.session.commit()
            paciente_id = paciente.id
            
            # Crear varias citas
            for i in range(3):
                cita = Cita(
                    paciente_id=paciente_id,
                    fecha=(datetime.now() + timedelta(days=i)).date(),
                    hora=datetime.now().time(),
                    motivo=f'Cita {i+1}',
                    estado='pendiente',
                    doctor='Dr. Test'
                )
                db.session.add(cita)
            db.session.commit()
        
        response = authenticated_client.get(f'/pacientes/{paciente_id}/citas')
        assert response.status_code == 200
