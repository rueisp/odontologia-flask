"""
Rutas HTTP para el módulo de pacientes.

Este módulo contiene solo las rutas HTTP, delegando la lógica de negocio
a pacientes_services.py para mejor mantenibilidad.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import date, datetime
from clinica.models import Paciente, PagoPaciente
from ..extensions import db
import json 
from sqlalchemy import or_
import cloudinary.uploader  # <--- AGREGA ESTO
from clinica.decorators.limites import verificar_limite_pacientes
from sqlalchemy.orm import load_only
from clinica.campos_activos import load_only_paciente_activo
# Importar servicios
# Importar servicios de pacientes
from .pacientes_services import (
    listar_pacientes_service,
    obtener_paciente_service,
    crear_paciente_service,
    editar_paciente_service,
    borrar_paciente_service,
    subir_dentigrama_service
)

# Importar servicios de evoluciones
from .pacientes_evoluciones import agregar_evolucion_service

pacientes_bp = Blueprint('pacientes', __name__, url_prefix='/pacientes')


@pacientes_bp.route('/crear', methods=['GET', 'POST'])
@login_required
def crear_paciente():
    """Crea un nuevo paciente"""
    if request.method == 'POST':
        resultado = crear_paciente_service(request.form, request.files, current_user)
        
        if resultado['success']:
            flash(resultado['message'], 'success')
            return redirect(url_for('pacientes.lista_pacientes'))
        else:
            flash(resultado['message'], 'danger')
            return render_template('registrar_paciente.html', paciente=None)
    
    # GET - Mostrar formulario vacío
    return render_template('registrar_paciente.html', paciente=None)


@pacientes_bp.route('/lista', methods=['GET'])
@login_required
def lista_pacientes():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('buscar', '').strip()
    
    # ✅ CONSULTA OPTIMIZADA - Solo campos activos
    query = db.session.query(Paciente).options(
        load_only_paciente_activo()
    ).filter(Paciente.is_deleted == False)

    # Filtrar por odontólogo si no es admin
    if not current_user.is_admin:
        query = query.filter(Paciente.odontologo_id == current_user.id)

    # Lógica de búsqueda
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            or_(
                Paciente.nombres.ilike(search_term),
                Paciente.apellidos.ilike(search_term),
                Paciente.documento.ilike(search_term)
            )
        )

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


@pacientes_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_paciente(id):
    """Edita un paciente existente - Versión simplificada"""
    
    if request.method == 'POST':
        # Procesar el formulario de edición
        resultado = editar_paciente_service(id, request.form, request.files, current_user)
        
        if resultado['success']:
            flash(resultado['message'], 'success')
            # Redirigir a la vista del paciente
            return redirect(url_for('pacientes.mostrar_paciente', id=id))
        else:
            flash(resultado['message'], 'danger')
            return redirect(url_for('pacientes.editar_paciente', id=id))

    # --- LÓGICA GET - USANDO EL SERVICIO OPTIMIZADO ---
    # Obtener datos del paciente con SOLO los campos necesarios
    paciente_data, evoluciones, public_id = obtener_paciente_service(id, current_user)
    
    # Convertir el diccionario a un objeto para el template
    from types import SimpleNamespace
    paciente = SimpleNamespace(**paciente_data)
    
    # Formatear fecha para el input type="date"
    if hasattr(paciente, 'fecha_nacimiento') and paciente.fecha_nacimiento and paciente.fecha_nacimiento != 'N/A':
        try:
            from datetime import datetime
            fecha_obj = datetime.strptime(paciente.fecha_nacimiento, '%d/%m/%Y')
            paciente.fecha_nacimiento = fecha_obj.strftime('%Y-%m-%d')
        except:
            paciente.fecha_nacimiento = ''

    # Renderizar template sin datos de ubicación
    return render_template('editar_paciente.html', 
                           paciente=paciente)

@pacientes_bp.route('/<int:id>/borrar', methods=['POST'])
@login_required
def borrar_paciente(id):
    """Borra un paciente (soft delete)"""
    resultado = borrar_paciente_service(id, current_user)
    flash(resultado['message'], 'success' if resultado['success'] else 'danger')
    return redirect(url_for('pacientes.lista_pacientes'))

# ============================================================
# RUTAS PARA CONTROL DE PAGOS DE PACIENTES
# ============================================================

@pacientes_bp.route('/<int:paciente_id>/pagos', methods=['GET'])
@login_required
def pagos_paciente(paciente_id):
    """Muestra el historial de pagos de un paciente"""
    from clinica.models import PagoPaciente, Paciente
    from datetime import date
    
    paciente = Paciente.query.filter_by(id=paciente_id, is_deleted=False).first_or_404()
    
    # Verificar permisos
    if not current_user.is_admin and paciente.odontologo_id != current_user.id:
        flash('No tienes permiso para ver este paciente.', 'danger')
        return redirect(url_for('pacientes.lista_pacientes'))
    
    pagos = PagoPaciente.query.filter_by(paciente_id=paciente_id).order_by(PagoPaciente.fecha.desc()).all()
    total_pagos = sum(p.monto for p in pagos)
    today = date.today().isoformat()
    
    return render_template('pacientes/pagos_paciente.html',
                         paciente=paciente,
                         pagos=pagos,
                         total_pagos=total_pagos,
                         today=today)


@pacientes_bp.route('/<int:paciente_id>/pagos/agregar', methods=['POST'])
@login_required
def agregar_pago_paciente(paciente_id):
    """Agrega un nuevo pago a un paciente"""
    from clinica.models import PagoPaciente, Paciente
    from clinica.extensions import db
    
    paciente = Paciente.query.filter_by(id=paciente_id, is_deleted=False).first_or_404()
    
    # Verificar permisos
    if not current_user.is_admin and paciente.odontologo_id != current_user.id:
        flash('No tienes permiso para modificar este paciente.', 'danger')
        return redirect(url_for('pacientes.lista_pacientes'))
    
    try:
        nuevo_pago = PagoPaciente(
            paciente_id=paciente_id,
            fecha=request.form.get('fecha'),
            descripcion=request.form.get('descripcion'),
            monto=int(request.form.get('monto', 0)),
            metodo_pago=request.form.get('metodo_pago'),
            observacion=request.form.get('observacion')
        )
        
        db.session.add(nuevo_pago)
        db.session.commit()
        
        flash('Pago registrado correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al registrar el pago: {str(e)}', 'danger')
    
    return redirect(url_for('pacientes.pagos_paciente', paciente_id=paciente_id))


# ============================================================
# RUTAS PARA EDITAR Y ELIMINAR PAGOS DE PACIENTES
# ============================================================

@pacientes_bp.route('/pago/<int:pago_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_pago_paciente(pago_id):
    """Edita un pago existente"""
    from clinica.models import PagoPaciente, Paciente
    
    pago = PagoPaciente.query.get_or_404(pago_id)
    paciente = Paciente.query.get_or_404(pago.paciente_id)
    
    # Verificar permisos
    if not current_user.is_admin and paciente.odontologo_id != current_user.id:
        flash('No tienes permiso para modificar este pago.', 'danger')
        return redirect(url_for('pacientes.lista_pacientes'))
    
    if request.method == 'POST':
        try:
            pago.fecha = request.form.get('fecha')
            pago.descripcion = request.form.get('descripcion')
            pago.monto = int(request.form.get('monto', 0))
            pago.metodo_pago = request.form.get('metodo_pago')
            pago.observacion = request.form.get('observacion')
            
            db.session.commit()
            flash('Pago actualizado correctamente.', 'success')
            return redirect(url_for('pacientes.pagos_paciente', paciente_id=paciente.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el pago: {str(e)}', 'danger')
            return redirect(url_for('pacientes.pagos_paciente', paciente_id=paciente.id))
    
    # GET: mostrar formulario con datos cargados
    today = date.today().isoformat()
    return render_template('pacientes/editar_pago_paciente.html',
                         pago=pago,
                         paciente=paciente,
                         today=today)


@pacientes_bp.route('/pago/<int:pago_id>/borrar', methods=['POST'])
@login_required
def borrar_pago_paciente(pago_id):
    """Elimina un pago"""
    from clinica.models import PagoPaciente, Paciente
    
    pago = PagoPaciente.query.get_or_404(pago_id)
    paciente = Paciente.query.get_or_404(pago.paciente_id)
    
    # Verificar permisos
    if not current_user.is_admin and paciente.odontologo_id != current_user.id:
        flash('No tienes permiso para eliminar este pago.', 'danger')
        return redirect(url_for('pacientes.lista_pacientes'))
    
    try:
        db.session.delete(pago)
        db.session.commit()
        flash('Pago eliminado correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el pago: {str(e)}', 'danger')
    
    return redirect(url_for('pacientes.pagos_paciente', paciente_id=paciente.id))


@pacientes_bp.route('/upload_dentigrama', methods=['POST'])
def upload_dentigrama():
    """
    Sube un dentigrama a Cloudinary.
    CONFIGURADO PARA SOBREESCRIBIR: Si hay patient_id, usa un nombre fijo
    para que Cloudinary reemplace la imagen anterior automáticamente.
    """
    try:
        data = request.get_json()
        image_data = data.get('image_data')
        patient_id = data.get('patient_id')

        if not image_data:
            return jsonify({'error': 'No hay datos de imagen'}), 400

        # LÓGICA DE NOMBRE ÚNICO (Public ID)
        public_id = None
        if patient_id and str(patient_id).strip() != "":
            # Al usar siempre el mismo nombre para el ID, Cloudinary borra la vieja
            public_id = f"dentigrama_paciente_{patient_id}"

        # Subida directa a Cloudinary con configuración de sobreescritura
        upload_result = cloudinary.uploader.upload(
            image_data,
            public_id=public_id,  # Nombre forzado (si existe ID)
            overwrite=True,       # ¡Importante! Sobreescribe si ya existe
            invalidate=True,      # Limpia la caché de la CDN para ver cambios inmediatos
            folder="dentigramas_pacientes" # Carpeta en Cloudinary
        )

        # Obtenemos la URL segura
        new_url = upload_result['secure_url']
        public_id_created = upload_result['public_id'] # <--- NUEVO
        
        return jsonify({
            'success': True, 
            'url': new_url, 
            'public_id': public_id_created, # <--- NUEVO: Lo devolvemos al front
            'message': 'Dentigrama procesado correctamente'
        }), 200
    
    except Exception as e:
        print(f"Error al subir dentigrama: {e}")
        return jsonify({'error': str(e)}), 500
    
@pacientes_bp.route('/obtener_paciente_ajax/<int:id>', methods=['GET'])
@login_required
def obtener_paciente_ajax(id):
    """Endpoint JSON para el panel derecho del dashboard"""
    try:
        from .pacientes_services import obtener_paciente_service
        from clinica.models import Cita
        from datetime import date, datetime
        from sqlalchemy import or_
        
        paciente_data, evoluciones, public_id = obtener_paciente_service(id, current_user)
        
        # --- OBTENER DATOS DE CITAS REALES ---
        # Última cita (fecha anterior a hoy)
        ultima_cita = Cita.query.filter(
            Cita.paciente_id == id,
            Cita.is_deleted == False,
            Cita.fecha < date.today()
        ).order_by(
            Cita.fecha.desc(), 
            Cita.hora.desc()
        ).first()
        
        # Próxima cita (fecha posterior a hoy, o hoy pero con hora posterior)
        proxima_cita = Cita.query.filter(
            Cita.paciente_id == id,
            Cita.is_deleted == False,
            or_(
                Cita.fecha > date.today(),
                (Cita.fecha == date.today()) & (Cita.hora > datetime.now().time())
            )
        ).order_by(Cita.fecha, Cita.hora).first()
        
        # Formatear última cita
        ultima_cita_info = "No hay citas anteriores"
        if ultima_cita:
            fecha_str = ultima_cita.fecha.strftime('%d/%m/%Y')
            hora_str = ultima_cita.hora.strftime('%H:%M') if ultima_cita.hora else ''
            motivo = ultima_cita.motivo or 'Sin motivo'
            ultima_cita_info = f"{fecha_str} {hora_str} - {motivo}"
        
        # Formatear próxima cita
        proxima_cita_info = "No tiene próximas citas"
        if proxima_cita:
            fecha_str = proxima_cita.fecha.strftime('%d/%m/%Y')
            hora_str = proxima_cita.hora.strftime('%H:%M') if proxima_cita.hora else ''
            motivo = proxima_cita.motivo or 'Sin motivo'
            proxima_cita_info = f"{fecha_str} {hora_str} - {motivo}"
        
        # Mapear los campos
        response_data = {
            'id': paciente_data.get('id'),
            'nombre': f"{paciente_data.get('primer_nombre', '')} {paciente_data.get('primer_apellido', '')}".strip(),
            'documento': paciente_data.get('documento', 'No especificado'),
            'telefono': paciente_data.get('telefono', 'No especificado'),
            'edad': paciente_data.get('edad', 'No especificada'),
            'fecha_nacimiento': paciente_data.get('fecha_nacimiento', 'No especificado'),
            'direccion': paciente_data.get('direccion', 'No especificado'),
            'barrio': paciente_data.get('barrio', 'No especificado'),
            'email': paciente_data.get('email', 'No especificado'),
            'alergias': paciente_data.get('alergias', 'No especificado'),
            'motivo_consulta': paciente_data.get('motivo_consulta', 'No especificado'),
            'enfermedad_actual': paciente_data.get('enfermedad_actual', 'No especificado'),
            'observaciones': paciente_data.get('observaciones', 'No especificado'),
            'dentigrama_url': paciente_data.get('dentigrama_canvas', None),
            'ultima_cita_info': ultima_cita_info,
            'proxima_cita_paciente_info': proxima_cita_info
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error en obtener_paciente_ajax: {e}")
        return jsonify({'error': str(e)}), 500