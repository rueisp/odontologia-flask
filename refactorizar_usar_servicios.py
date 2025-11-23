#!/usr/bin/env python3
"""
Script para refactorizar pacientes.py para usar los servicios
"""

import re
from pathlib import Path

def refactorizar_pacientes_usar_servicios():
    """Refactoriza pacientes.py para usar pacientes_services.py"""
    
    archivo = Path("clinica/routes/pacientes.py")
    contenido = archivo.read_text(encoding='utf-8')
    
    # Nuevo contenido del archivo
    nuevo_contenido = '''"""
Rutas HTTP para el módulo de pacientes.

Este módulo contiene solo las rutas HTTP, delegando la lógica de negocio
a pacientes_services.py para mejor mantenibilidad.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import date, datetime

# Importar servicios
from .pacientes_services import (
    listar_pacientes_service,
    obtener_paciente_service,
    agregar_evolucion_service,
    crear_paciente_service,
    editar_paciente_service,
    borrar_paciente_service,
    subir_dentigrama_service
)


pacientes_bp = Blueprint('pacientes', __name__, url_prefix='/pacientes')


@pacientes_bp.route('/')
@login_required
def lista_pacientes():
    """Lista paginada de pacientes"""
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('buscar', '').strip()
    pacientes = listar_pacientes_service(current_user, page, search_term)
    return render_template('pacientes.html', pacientes=pacientes, buscar=search_term)


@pacientes_bp.route('/<int:id>', methods=['GET', 'POST'])
@login_required
def mostrar_paciente(id):
    """Muestra un paciente y permite agregar evoluciones"""
    if request.method == 'POST':
        descripcion = request.form.get('descripcion')
        resultado = agregar_evolucion_service(id, descripcion, current_user)
        flash(resultado['message'], 'success' if resultado['success'] else 'warning')
        return redirect(url_for('pacientes.mostrar_paciente', id=id))

    paciente_data, evoluciones_procesadas, full_public_id_trazos = obtener_paciente_service(id, current_user)
    
    return render_template('mostrar_paciente.html',
                          paciente=paciente_data,
                          evoluciones_ordenadas=evoluciones_procesadas,
                          full_public_id_trazos=full_public_id_trazos,
                          current_full_path=request.full_path)


@pacientes_bp.route('/crear', methods=['GET', 'POST'])
@login_required
def crear_paciente():
    """Crea un nuevo paciente"""
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        resultado = crear_paciente_service(request.form, request.files, current_user)
        
        if is_ajax:
            if resultado['success']:
                return jsonify({
                    'success': True,
                    'message': resultado['message'],
                    'redirect_url': url_for('pacientes.lista_pacientes')
                }), 200
            else:
                return jsonify({'success': False, 'error': resultado['message']}), 400
        
        if resultado['success']:
            flash(resultado['message'], 'success')
            return redirect(url_for('pacientes.lista_pacientes'))
        else:
            flash(resultado['message'], 'danger')
            # Mantener los datos del formulario en caso de error
            from ..models import Paciente
            paciente_temporal = Paciente()
            return render_template('registrar_paciente.html', paciente=paciente_temporal)

    # GET request
    from ..models import Paciente
    paciente_vacio = Paciente()
    paciente_vacio.fecha_nacimiento = ''
    return render_template('registrar_paciente.html', paciente=paciente_vacio)


@pacientes_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_paciente(id):
    """Edita un paciente existente"""
    if request.method == 'POST':
        resultado = editar_paciente_service(id, request.form, request.files, current_user)
        
        if resultado['success']:
            flash(resultado['message'], 'success')
            return jsonify({
                'message': resultado['message'],
                'redirect_url': url_for('pacientes.mostrar_paciente', id=id)
            }), 200
        else:
            return jsonify({'error': resultado['message']}), 500

    # GET request
    from ..models import Paciente
    query = Paciente.query.filter_by(id=id, is_deleted=False)
    if not current_user.is_admin:
        query = query.filter_by(odontologo_id=current_user.id)
    paciente = query.first_or_404()
    
    # Formatear fecha para el formulario
    if isinstance(paciente.fecha_nacimiento, (date, datetime)):
        paciente.fecha_nacimiento = paciente.fecha_nacimiento.strftime('%Y-%m-%d')
    else:
        paciente.fecha_nacimiento = ''

    return render_template('editar_paciente.html', paciente=paciente)


@pacientes_bp.route('/<int:id>/borrar', methods=['POST'])
@login_required
def borrar_paciente(id):
    """Borra un paciente (soft delete)"""
    resultado = borrar_paciente_service(id, current_user)
    flash(resultado['message'], 'success' if resultado['success'] else 'danger')
    return redirect(url_for('pacientes.lista_pacientes'))


@pacientes_bp.route('/upload_dentigrama', methods=['POST'])
def upload_dentigrama():
    """Sube un dentigrama a Cloudinary"""
    data = request.get_json()
    image_data = data.get('image_data')
    patient_id = data.get('patient_id')
    
    resultado = subir_dentigrama_service(image_data, patient_id)
    
    if resultado['success']:
        return jsonify({'url': resultado['url'], 'message': resultado['message']}), 200
    else:
        return jsonify({'error': resultado['message']}), 400 if 'datos' in resultado['message'] else 500
'''
    
    # Guardar el nuevo contenido
    archivo.write_text(nuevo_contenido, encoding='utf-8')
    
    print("✅ pacientes.py refactorizado exitosamente")
    print(f"   Líneas antes: {len(contenido.splitlines())}")
    print(f"   Líneas después: {len(nuevo_contenido.splitlines())}")
    print(f"   Reducción: {len(contenido.splitlines()) - len(nuevo_contenido.splitlines())} líneas")
    
    return True

if __name__ == "__main__":
    try:
        refactorizar_pacientes_usar_servicios()
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
