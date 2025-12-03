"""
Rutas HTTP para el módulo de pacientes.

Este módulo contiene solo las rutas HTTP, delegando la lógica de negocio
a pacientes_services.py para mejor mantenibilidad.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import date, datetime
from clinica.models import Paciente, EPS, Municipio
from ..extensions import db
import json 
from sqlalchemy import or_
from clinica.decorators.limites import verificar_limite_pacientes
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


@pacientes_bp.route('/lista', methods=['GET'])
@login_required
def lista_pacientes():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('buscar', '').strip() # Obtener lo que escribes en el buscador
    
    # Consulta base
    query = Paciente.query

    # ▼▼▼ LÓGICA DE BÚSQUEDA (ESTO ES LO QUE PROBABLEMENTE FALTA) ▼▼▼
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            or_(
                Paciente.nombres.ilike(search_term),
                Paciente.apellidos.ilike(search_term),
                Paciente.documento.ilike(search_term)
            )
        )
    # ▲▲▲ FIN LÓGICA DE BÚSQUEDA ▲▲▲

    # Ordenar y paginar
    pacientes = query.order_by(Paciente.id.desc()).paginate(page=page, per_page=6, error_out=False)

    return render_template('pacientes.html', pacientes=pacientes, buscar=search_query)

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


# En clinica/routes/pacientes.py

# ... (asegúrate de tener todas tus importaciones al principio: Blueprint, jsonify, etc.)

@pacientes_bp.route('/crear', methods=['GET', 'POST'])
@login_required
@verificar_limite_pacientes  # ← NUEVO DECORADOR
def crear_paciente():
    """Crea un nuevo paciente y maneja respuestas tanto AJAX como normales."""

    # --- LÓGICA PARA CARGAR DATOS (tu código original, perfecto) ---
    eps_list = EPS.query.filter_by(activa=True).order_by(EPS.nombre).all()
    departamentos_query = db.session.query(
        Municipio.codigo_departamento, 
        Municipio.nombre_departamento
    ).distinct().order_by(Municipio.nombre_departamento).all()
    departamentos_list = [{'codigo': d.codigo_departamento, 'nombre': d.nombre_departamento} for d in departamentos_query]
    
    municipios = Municipio.query.order_by(Municipio.nombre).all()
    municipios_json = json.dumps([m.to_dict() for m in municipios])


    # ===================================================================
    # ▼▼▼ SECCIÓN POST MODIFICADA PARA RESPONDER JSON ▼▼▼
    # ===================================================================
    if request.method == 'POST':
        # Llamamos a tu servicio, que ya funciona y guarda los datos
        resultado = crear_paciente_service(request.form, request.files, current_user)
        
        if resultado['success']:
            # Si el guardado fue exitoso, creamos una respuesta JSON de éxito.
            # El JavaScript usará 'redirect_url' para saber a dónde ir.
            return jsonify({
                'success': True,
                'message': resultado['message'],
                'redirect_url': url_for('pacientes.lista_pacientes')
            }), 200
        else:
            # Si el servicio devolvió un error, creamos una respuesta JSON de error.
            # El JavaScript mostrará el 'error' en un alert.
            return jsonify({
                'success': False,
                'error': resultado['message']
            }), 400 # 400 es un código de "Bad Request", apropiado para un error de formulario.

    # ===================================================================
    # ▲▲▲ FIN DE LA SECCIÓN POST MODIFICADA ▲▲▲
    # ===================================================================

    # --- MANEJO DE LA PETICIÓN GET (tu código original, perfecto) ---
    paciente_vacio = Paciente()
    return render_template('registrar_paciente.html', 
                         paciente=paciente_vacio,
                         eps_list=eps_list,
                         departamentos_list=departamentos_list,
                         municipios_json=municipios_json)


@pacientes_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_paciente(id):
    """Edita un paciente existente"""

    # --- LÓGICA PARA CARGAR DATOS DE LOS SELECTORES (AÑADIDA) ---
    # La necesitamos en el GET para mostrar el formulario y en el POST si hubiera un error que re-renderice
    eps_list = EPS.query.filter_by(activa=True).order_by(EPS.nombre).all()
    departamentos_query = db.session.query(
        Municipio.codigo_departamento, 
        Municipio.nombre_departamento
    ).distinct().order_by(Municipio.nombre_departamento).all()
    departamentos_list = [{'codigo': d.codigo_departamento, 'nombre': d.nombre_departamento} for d in departamentos_query]
    
    municipios = Municipio.query.order_by(Municipio.nombre).all()
    # Asumiendo que tienes un método to_dict() en el modelo Municipio
    municipios_json = json.dumps([m.to_dict() for m in municipios])


    # --- LÓGICA POST (sin cambios) ---
    if request.method == 'POST':
        # Tu lógica de servicio se encarga de procesar los datos, incluyendo los nuevos campos
        # 'codigo_dpto' y 'codigo_mpio' que vendrán en request.form
        resultado = editar_paciente_service(id, request.form, request.files, current_user)
        
        if resultado['success']:
            flash(resultado['message'], 'success')
            return jsonify({
                'message': resultado['message'],
                'redirect_url': url_for('pacientes.mostrar_paciente', id=id)
            }), 200
        else:
            return jsonify({'error': resultado['message']}), 500

    # --- LÓGICA GET (MODIFICADA) ---
    # Buscamos al paciente a editar
    query = Paciente.query.filter_by(id=id, is_deleted=False)
    if not current_user.is_admin:
        query = query.filter_by(odontologo_id=current_user.id)
    paciente = query.first_or_404()
    
    # Formatear fecha para el formulario (tu código original)
    if isinstance(paciente.fecha_nacimiento, (date, datetime)):
        paciente.fecha_nacimiento = paciente.fecha_nacimiento.strftime('%Y-%m-%d')
    else:
        paciente.fecha_nacimiento = ''

    # --- Renderizamos la plantilla pasando TODOS los datos necesarios ---
    return render_template('editar_paciente.html', 
                           paciente=paciente,
                           eps_list=eps_list,
                           departamentos_list=departamentos_list,
                           municipios_json=municipios_json)
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
