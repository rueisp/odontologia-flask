"""
Servicios de lógica de negocio para el módulo de pacientes.

Este módulo contiene toda la lógica de negocio relacionada con pacientes,
separada de las rutas HTTP para mejor mantenibilidad y testabilidad.
"""

import os
import uuid
from datetime import datetime, date
import cloudinary
import cloudinary.uploader
import pytz
from flask import request, jsonify, flash, current_app
from sqlalchemy import or_
from ..extensions import db
from ..models import Paciente, Cita, Evolucion, AuditLog
from ..utils import allowed_file, convertir_a_fecha, extract_public_id_from_url


# =========================================================================
# === FUNCIONES AUXILIARES PARA CLOUDINARY ===
# =========================================================================

def upload_file_to_cloudinary(file, folder_name="general_uploads"):
    """Sube un objeto FileStorage a Cloudinary y devuelve su URL segura.
    
    Args:
        file: Objeto FileStorage de Flask
        folder_name: Nombre de la carpeta en Cloudinary
        
    Returns:
        str: URL segura del archivo subido, o None si falla
    """
    if not file:
        current_app.logger.debug(f"CLOUDINARY_UPLOAD_DEBUG: No se proporcionó ningún objeto 'file' para subir a '{folder_name}'.")
        return None
    
    if file.filename == '':
        current_app.logger.debug(f"CLOUDINARY_UPLOAD_DEBUG: El nombre del archivo está vacío para subir a '{folder_name}'.")
        return None
    
    if not allowed_file(file.filename):
        current_app.logger.warning(f"CLOUDINARY_UPLOAD_WARNING: Tipo de archivo no permitido para '{file.filename}' en la carpeta '{folder_name}'.")
        return None

    try:
        current_app.logger.info(f"CLOUDINARY_UPLOAD_INFO: Intentando subir '{file.filename}' a Cloudinary en la carpeta '{folder_name}'.")
        upload_result = cloudinary.uploader.upload(file, folder=folder_name)
        secure_url = upload_result.get('secure_url')
        if secure_url:
            current_app.logger.info(f"CLOUDINARY_UPLOAD_SUCCESS: Archivo '{file.filename}' subido exitosamente a '{folder_name}'. URL: {secure_url}")
        else:
            current_app.logger.error(f"CLOUDINARY_UPLOAD_ERROR: Se subió el archivo '{file.filename}' pero no se obtuvo 'secure_url' en el resultado: {upload_result}", exc_info=True)
        return secure_url
    except Exception as e:
        current_app.logger.error(f"CLOUDINARY_UPLOAD_ERROR: Error al subir archivo '{file.filename}' a Cloudinary en '{folder_name}': {e}", exc_info=True)
        return None


def delete_from_cloudinary(url):
    """Borra un recurso de Cloudinary dada su URL.
    
    Args:
        url: URL del recurso en Cloudinary
        
    Returns:
        bool: True si se eliminó exitosamente, False en caso contrario
    """
    if url:
        public_id = extract_public_id_from_url(url)
        if public_id:
            try:
                cloudinary.uploader.destroy(public_id)
                current_app.logger.debug(f"CLOUDINARY: Recurso {public_id} eliminado exitosamente.")
                return True
            except Exception as e:
                current_app.logger.error(f"Error al eliminar recurso {public_id} de Cloudinary: {e}", exc_info=True)
                return False
    return False


def procesar_subida_imagen(file_key, folder_name, is_ajax=False):
    """Procesa la subida de una imagen desde request.files.
    
    Args:
        file_key: Clave en request.files
        folder_name: Carpeta en Cloudinary
        is_ajax: Si la petición es AJAX
        
    Returns:
        tuple: (url, error_response)
    """
    if file_key not in request.files:
        return None, None
    
    file = request.files[file_key]
    if not file or file.filename == '':
        return None, None
    
    if not allowed_file(file.filename):
        error_msg = f'Tipo de archivo no permitido para {file_key}. Solo se permiten imágenes.'
        current_app.logger.warning(f"SUBIDA_IMAGEN_ERROR: {error_msg}")
        if is_ajax:
            return None, jsonify({'success': False, 'error': error_msg})
        flash(error_msg, 'warning')
        return None, None
    
    url = upload_file_to_cloudinary(file, folder_name=folder_name)
    if not url:
        error_msg = f'Error al subir {file_key} a Cloudinary.'
        current_app.logger.error(f"SUBIDA_IMAGEN_ERROR: {error_msg}")
        if is_ajax:
            return None, jsonify({'success': False, 'error': error_msg})
        flash(error_msg, 'warning')
        return None, None
    
    return url, None


def eliminar_imagenes_paciente(paciente, log_prefix="PACIENTE"):
    """Elimina todas las imágenes de un paciente de Cloudinary.
    
    Args:
        paciente: Objeto Paciente
        log_prefix: Prefijo para los logs
    """
    imagenes = {
        'imagen_perfil_url': paciente.imagen_perfil_url,
        'imagen_1': paciente.imagen_1,
        'imagen_2': paciente.imagen_2,
        'dentigrama_canvas': paciente.dentigrama_canvas
    }
    
    for campo, url in imagenes.items():
        if url:
            if delete_from_cloudinary(url):
                setattr(paciente, campo, None)
                current_app.logger.debug(f"{log_prefix}: {campo} eliminada de Cloudinary")
            else:
                current_app.logger.warning(f"{log_prefix}: Falló eliminación de {campo}")


# =========================================================================
# === SERVICIOS DE LÓGICA DE NEGOCIO ===
# =========================================================================

def listar_pacientes_service(usuario, page, search_term):
    """Obtiene la lista paginada de pacientes para un usuario.
    
    Args:
        usuario: Usuario actual
        page: Número de página
        search_term: Término de búsqueda
        
    Returns:
        Pagination: Objeto de paginación con los pacientes
    """
    query = Paciente.query.filter(Paciente.is_deleted == False)

    if not usuario.is_admin:
        query = query.filter(Paciente.odontologo_id == usuario.id)

    if search_term:
        query = query.filter(
            or_(
                Paciente.nombres.ilike(f"%{search_term}%"),
                Paciente.apellidos.ilike(f"%{search_term}%"),
                Paciente.documento.ilike(f"%{search_term}%")
            )
        )
    
    pacientes = query.order_by(Paciente.apellidos, Paciente.nombres).paginate(
        page=page, per_page=7, error_out=False
    )
    
    current_app.logger.debug(f"Usuario: {usuario.username}, es admin: {usuario.is_admin}")
    current_app.logger.debug(f"Pacientes encontrados para este usuario: {pacientes.total}")

    return pacientes


def obtener_paciente_service(paciente_id, usuario):
    """Obtiene un paciente y prepara sus datos para mostrar.
    
    Args:
        paciente_id: ID del paciente
        usuario: Usuario actual
        
    Returns:
        tuple: (paciente_data, evoluciones_procesadas, full_public_id_trazos)
    """
    query = Paciente.query.filter_by(id=paciente_id, is_deleted=False)
    if not usuario.is_admin:
        query = query.filter_by(odontologo_id=usuario.id)
    paciente = query.first_or_404()

    # Preparar datos del paciente para la plantilla
    paciente_data = {
        'id': paciente.id,
        'nombres': paciente.nombres or 'N/A',
        'apellidos': paciente.apellidos or 'N/A',
        'tipo_documento': paciente.tipo_documento or '',
        'documento': paciente.documento or 'N/A',
        'telefono': paciente.telefono or 'N/A',
        'email': paciente.email or 'N/A',
        'fecha_nacimiento': paciente.fecha_nacimiento.strftime('%d/%m/%Y') if isinstance(paciente.fecha_nacimiento, (date, datetime)) else 'N/A',
        'edad': f"{paciente.edad} años" if paciente.edad is not None else 'N/A',
        'genero': paciente.genero or 'N/A',
        'estado_civil': paciente.estado_civil or 'N/A',
        'ocupacion': paciente.ocupacion or 'N/A',
        'dentigrama_canvas': paciente.dentigrama_canvas,
        'imagen_perfil_url': paciente.imagen_perfil_url,
        'imagen_1': paciente.imagen_1,
        'imagen_2': paciente.imagen_2,
        'direccion': paciente.direccion or 'N/A',
        'barrio': paciente.barrio or 'N/A',
        'municipio': paciente.municipio or 'N/A',
        'departamento': paciente.departamento or 'N/A',
        'aseguradora': paciente.aseguradora or 'N/A',
        'tipo_vinculacion': paciente.tipo_vinculacion or 'N/A',
        'referido_por': paciente.referido_por or 'N/A',
        'nombre_responsable': paciente.nombre_responsable or 'N/A',
        'telefono_responsable': paciente.telefono_responsable or 'N/A',
        'parentesco': paciente.parentesco or 'N/A',
        'motivo_consulta': paciente.motivo_consulta or 'No especificado',
        'enfermedad_actual': paciente.enfermedad_actual or 'No especificado',
        'antecedentes_personales': paciente.antecedentes_personales or 'No especificado',
        'antecedentes_familiares': paciente.antecedentes_familiares or 'No especificado',
        'antecedentes_quirurgicos': paciente.antecedentes_quirurgicos or 'No especificado',
        'antecedentes_hemorragicos': paciente.antecedentes_hemorragicos or 'No especificado',
        'farmacologicos': paciente.farmacologicos or 'No especificado',
        'reaccion_medicamentos': paciente.reaccion_medicamentos or 'No especificado',
        'alergias': paciente.alergias or 'No especificado',
        'habitos': paciente.habitos or 'No especificado',
        'cepillado': paciente.cepillado or 'No especificado',
        'examen_fisico': paciente.examen_fisico or 'No especificado',
        'ultima_visita_odontologo': paciente.ultima_visita_odontologo or 'No especificado',
        'plan_tratamiento': paciente.plan_tratamiento or 'No especificado',
        'observaciones': paciente.observaciones or 'No especificado',
    }

    # Preparar evoluciones
    evoluciones_procesadas = []
    if paciente.evoluciones:
        evoluciones_ordenadas = sorted(paciente.evoluciones, key=lambda evo: evo.fecha, reverse=True)
        for evolucion_obj in evoluciones_ordenadas:
            evoluciones_procesadas.append({
                'id': evolucion_obj.id,
                'descripcion': evolucion_obj.descripcion,
                'fecha_formateada': evolucion_obj.fecha.strftime('%d de %B, %Y') if isinstance(evolucion_obj.fecha, (date, datetime)) else 'N/A'
            })

    # Extraer Public ID del dentigrama
    full_public_id_trazos = None
    if paciente.dentigrama_canvas:
        try:
            full_public_id_trazos = extract_public_id_from_url(paciente.dentigrama_canvas)
        except Exception as e:
            current_app.logger.error(f"DENTIGRAMA ERROR (Backend): Error al extraer public ID de dentigrama_canvas: {e}")
            full_public_id_trazos = None

    return paciente_data, evoluciones_procesadas, full_public_id_trazos


def agregar_evolucion_service(paciente_id, descripcion, usuario):
    """Agrega una evolución a un paciente.
    
    Args:
        paciente_id: ID del paciente
        descripcion: Descripción de la evolución
        usuario: Usuario actual
        
    Returns:
        dict: {'success': bool, 'message': str}
    """
    query = Paciente.query.filter_by(id=paciente_id, is_deleted=False)
    if not usuario.is_admin:
        query = query.filter_by(odontologo_id=usuario.id)
    paciente = query.first_or_404()

    if not descripcion or not descripcion.strip():
        return {'success': False, 'message': 'La descripción de la evolución no puede estar vacía.'}

    local_timezone = pytz.timezone('America/Bogota')
    now_in_local_tz = datetime.now(local_timezone)
    fecha_local = now_in_local_tz.date()

    nueva_evolucion = Evolucion(
        descripcion=descripcion.strip(),
        paciente_id=paciente.id,
        fecha=fecha_local
    )
    db.session.add(nueva_evolucion)
    
    try:
        db.session.commit()
        return {'success': True, 'message': 'Evolución añadida correctamente.'}
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al añadir evolución para paciente {paciente.id}: {e}", exc_info=True)
        return {'success': False, 'message': 'Ocurrió un error al guardar la evolución.'}


def crear_paciente_service(form_data, files, usuario):
    """Crea un nuevo paciente con validación y manejo de imágenes.
    
    Args:
        form_data: Datos del formulario
        files: Archivos subidos
        usuario: Usuario actual
        
    Returns:
        dict: {'success': bool, 'message': str, 'paciente_id': int (opcional)}
    """
    # Validación de documento
    documento = form_data.get('documento')
    if not documento:
        return {'success': False, 'message': 'El número de documento es obligatorio.'}

    paciente_existente = Paciente.query.filter_by(documento=documento, is_deleted=False).first()
    if paciente_existente:
        return {'success': False, 'message': f'Ya existe un paciente registrado con el documento {documento}.'}
    
    try:
        # Crear paciente con datos del formulario
        nuevo_paciente = Paciente(
            nombres=form_data.get('nombres'),
            apellidos=form_data.get('apellidos'),
            tipo_documento=form_data.get('tipo_documento'),
            documento=documento,
            fecha_nacimiento=convertir_a_fecha(form_data.get('fecha_nacimiento')),
            telefono=form_data.get('telefono'),
            edad=int(form_data.get('edad')) if form_data.get('edad') else None,
            email=form_data.get('email'),
            genero=form_data.get('genero'),
            estado_civil=form_data.get('estado_civil'),
            direccion=form_data.get('direccion'),
            barrio=form_data.get('barrio'),
            municipio=form_data.get('municipio'),
            departamento=form_data.get('departamento'),
            aseguradora=form_data.get('aseguradora'),
            tipo_vinculacion=form_data.get('tipo_vinculacion'),
            ocupacion=form_data.get('ocupacion'),
            referido_por=form_data.get('referido_por'),
            nombre_responsable=form_data.get('nombre_responsable'),
            telefono_responsable=form_data.get('telefono_responsable'),
            parentesco=form_data.get('parentesco'),
            motivo_consulta=form_data.get('motivo_consulta'),
            enfermedad_actual=form_data.get('enfermedad_actual'),
            antecedentes_personales=form_data.get('antecedentes_personales'),
            antecedentes_familiares=form_data.get('antecedentes_familiares'),
            antecedentes_quirurgicos=form_data.get('antecedentes_quirurgicos'),
            antecedentes_hemorragicos=form_data.get('antecedentes_hemorragicos'),
            farmacologicos=form_data.get('farmacologicos'),
            reaccion_medicamentos=form_data.get('reaccion_medicamentos'),
            alergias=form_data.get('alergias'),
            habitos=form_data.get('habitos'),
            cepillado=form_data.get('cepillado'),
            examen_fisico=form_data.get('examen_fisico'),
            ultima_visita_odontologo=form_data.get('ultima_visita_odontologo', ''),
            plan_tratamiento=form_data.get('plan_tratamiento'),
            observaciones=form_data.get('observaciones', ''),
            dentigrama_canvas=form_data.get('dentigrama_canvas') or None,
            odontologo_id=usuario.id
        )

        # Procesar imágenes (manteniendo lógica original por compatibilidad)
        if 'imagen_perfil' in files:
            file_perfil = files['imagen_perfil']
            if file_perfil and file_perfil.filename != '' and allowed_file(file_perfil.filename):
                nuevo_paciente.imagen_perfil_url = upload_file_to_cloudinary(file_perfil, folder_name="pacientes_perfil")

        if 'imagen_1' in files:
            file_imagen_1 = files['imagen_1']
            if file_imagen_1 and file_imagen_1.filename != '' and allowed_file(file_imagen_1.filename):
                nuevo_paciente.imagen_1 = upload_file_to_cloudinary(file_imagen_1, folder_name="paciente_imagenes")

        if 'imagen_2' in files:
            file_imagen_2 = files['imagen_2']
            if file_imagen_2 and file_imagen_2.filename != '' and allowed_file(file_imagen_2.filename):
                nuevo_paciente.imagen_2 = upload_file_to_cloudinary(file_imagen_2, folder_name="paciente_imagenes")

        db.session.add(nuevo_paciente)
        db.session.commit()

        return {'success': True, 'message': 'Paciente guardado con éxito', 'paciente_id': nuevo_paciente.id}

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error FATAL al guardar paciente: {e}', exc_info=True)
        return {'success': False, 'message': 'Ocurrió un error inesperado al guardar el paciente.'}


def editar_paciente_service(paciente_id, form_data, files, usuario):
    """Edita un paciente existente.
    
    Args:
        paciente_id: ID del paciente
        form_data: Datos del formulario
        files: Archivos subidos
        usuario: Usuario actual
        
    Returns:
        dict: {'success': bool, 'message': str}
    """
    query = Paciente.query.filter_by(id=paciente_id, is_deleted=False)
    if not usuario.is_admin:
        query = query.filter_by(odontologo_id=usuario.id)
    paciente = query.first_or_404()
    
    try:
        # Actualizar campos de texto
        paciente.nombres = form_data.get('nombres')
        paciente.apellidos = form_data.get('apellidos')
        paciente.tipo_documento = form_data.get('tipo_documento')
        paciente.documento = form_data.get('documento')
        paciente.email = form_data.get('email')
        paciente.fecha_nacimiento = convertir_a_fecha(form_data.get('fecha_nacimiento', ''))
        paciente.edad = form_data.get('edad', type=int)
        paciente.telefono = form_data.get('telefono')
        paciente.genero = form_data.get('genero')
        paciente.estado_civil = form_data.get('estado_civil')
        paciente.direccion = form_data.get('direccion')
        paciente.barrio = form_data.get('barrio')
        paciente.municipio = form_data.get('municipio')
        paciente.departamento = form_data.get('departamento')
        paciente.aseguradora = form_data.get('aseguradora')
        paciente.tipo_vinculacion = form_data.get('tipo_vinculacion')
        paciente.ocupacion = form_data.get('ocupacion')
        paciente.referido_por = form_data.get('referido_por')
        paciente.nombre_responsable = form_data.get('nombre_responsable')
        paciente.telefono_responsable = form_data.get('telefono_responsable')
        paciente.parentesco = form_data.get('parentesco')
        paciente.motivo_consulta = form_data.get('motivo_consulta')
        paciente.enfermedad_actual = form_data.get('enfermedad_actual')
        paciente.antecedentes_personales = form_data.get('antecedentes_personales')
        paciente.antecedentes_familiares = form_data.get('antecedentes_familiares')
        paciente.antecedentes_quirurgicos = form_data.get('antecedentes_quirurgicos')
        paciente.antecedentes_hemorragicos = form_data.get('antecedentes_hemorragicos')
        paciente.farmacologicos = form_data.get('farmacologicos')
        paciente.reaccion_medicamentos = form_data.get('reaccion_medicamentos')
        paciente.alergias = form_data.get('alergias')
        paciente.habitos = form_data.get('habitos')
        paciente.cepillado = form_data.get('cepillado')
        paciente.examen_fisico = form_data.get('examen_fisico')
        paciente.ultima_visita_odontologo = form_data.get('ultima_visita_odontologo')
        paciente.plan_tratamiento = form_data.get('plan_tratamiento')
        paciente.observaciones = form_data.get('observaciones')

        # Manejo de eliminación de imágenes
        if 'eliminar_imagen_perfil' in form_data and paciente.imagen_perfil_url:
            delete_from_cloudinary(paciente.imagen_perfil_url)
            paciente.imagen_perfil_url = None

        if 'eliminar_imagen_1' in form_data and paciente.imagen_1:
            delete_from_cloudinary(paciente.imagen_1)
            paciente.imagen_1 = None
        
        if 'eliminar_imagen_2' in form_data and paciente.imagen_2:
            delete_from_cloudinary(paciente.imagen_2)
            paciente.imagen_2 = None

        # Manejo de subida de nuevas imágenes
        if 'imagen_perfil' in files:
            file_perfil = files['imagen_perfil']
            if file_perfil and file_perfil.filename != '':
                if paciente.imagen_perfil_url:
                    delete_from_cloudinary(paciente.imagen_perfil_url)
                nueva_url = upload_file_to_cloudinary(file_perfil, folder_name="pacientes_perfil")
                if nueva_url:
                    paciente.imagen_perfil_url = nueva_url

        if 'imagen_1' in files:
            imagen_1_file = files['imagen_1']
            if imagen_1_file and imagen_1_file.filename != '':
                if paciente.imagen_1:
                    delete_from_cloudinary(paciente.imagen_1)
                nueva_url = upload_file_to_cloudinary(imagen_1_file, folder_name="paciente_imagenes")
                if nueva_url:
                    paciente.imagen_1 = nueva_url

        if 'imagen_2' in files:
            imagen_2_file = files['imagen_2']
            if imagen_2_file and imagen_2_file.filename != '':
                if paciente.imagen_2:
                    delete_from_cloudinary(paciente.imagen_2)
                nueva_url = upload_file_to_cloudinary(imagen_2_file, folder_name="paciente_imagenes")
                if nueva_url:
                    paciente.imagen_2 = nueva_url

        # Manejo del dentigrama
        dentigrama_canvas_from_form = form_data.get('dentigrama_canvas')
        if dentigrama_canvas_from_form:
            if paciente.dentigrama_canvas and paciente.dentigrama_canvas != dentigrama_canvas_from_form:
                delete_from_cloudinary(paciente.dentigrama_canvas)
            paciente.dentigrama_canvas = dentigrama_canvas_from_form
        elif not dentigrama_canvas_from_form and paciente.dentigrama_canvas:
            delete_from_cloudinary(paciente.dentigrama_canvas)
            paciente.dentigrama_canvas = None

        db.session.commit()
        return {'success': True, 'message': 'Paciente actualizado correctamente'}

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error al editar paciente {paciente_id}: {e}', exc_info=True)
        return {'success': False, 'message': f'Error al actualizar el paciente: {str(e)}'}


def borrar_paciente_service(paciente_id, usuario):
    """Borra un paciente (soft delete) y sus imágenes.
    
    Args:
        paciente_id: ID del paciente
        usuario: Usuario actual
        
    Returns:
        dict: {'success': bool, 'message': str}
    """
    query = Paciente.query.filter_by(id=paciente_id)
    if not usuario.is_admin:
        query = query.filter_by(odontologo_id=usuario.id)
    paciente = query.first_or_404()
    
    if paciente.is_deleted:
        return {'success': False, 'message': f"El paciente '{paciente.nombres} {paciente.apellidos}' ya se encuentra en la papelera."}

    paciente_nombre_completo = f"{paciente.nombres} {paciente.apellidos}"
    
    try:
        # Eliminar imágenes de Cloudinary
        current_app.logger.info(f"PACIENTE_BORRADO: Iniciando eliminación de imágenes para paciente ID {paciente.id}")
        eliminar_imagenes_paciente(paciente, log_prefix="PACIENTE_BORRADO")
        current_app.logger.info(f"PACIENTE_BORRADO: Finalizada eliminación de imágenes para paciente ID {paciente.id}")

        # Soft delete del paciente
        paciente.is_deleted = True
        paciente.deleted_at = datetime.utcnow()

        # Soft delete en cascada para las citas
        citas_del_paciente = Cita.query.filter_by(paciente_id=paciente.id, is_deleted=False).all()
        for cita_item in citas_del_paciente:
            cita_item.is_deleted = True
            cita_item.deleted_at = datetime.utcnow()

        # Crear log de auditoría
        log_descripcion = f"Paciente '{paciente_nombre_completo}' movido a la papelera."
        if citas_del_paciente:
            log_descripcion += f" También se movieron {len(citas_del_paciente)} cita(s) asociadas."
            
        audit_entry = AuditLog(
            action_type="SOFT_DELETE_PACIENTE",
            description=log_descripcion,
            target_model="Paciente",
            target_id=paciente.id,
            user_id=usuario.id,
            user_username=usuario.username
        )
        db.session.add(audit_entry)
        db.session.commit()
        
        return {'success': True, 'message': f"Paciente '{paciente_nombre_completo}' movido a la papelera."}

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al mover paciente ID {paciente_id} a la papelera: {str(e)}", exc_info=True)
        return {'success': False, 'message': 'Ocurrió un error al mover el paciente a la papelera.'}


def subir_dentigrama_service(image_data, patient_id):
    """Sube un dentigrama a Cloudinary.
    
    Args:
        image_data: Datos Base64 de la imagen
        patient_id: ID del paciente (puede ser None para temporal)
        
    Returns:
        dict: {'success': bool, 'url': str (opcional), 'message': str}
    """
    if not image_data:
        current_app.logger.error("UPLOAD_DENTIGRAMA_ERROR: No se proporcionaron datos de imagen.")
        return {'success': False, 'message': 'No se proporcionaron datos de imagen'}

    try:
        patient = None
        old_dentigrama_url = None

        if patient_id:
            patient = Paciente.query.get(patient_id)
            if not patient:
                current_app.logger.warning(f"UPLOAD_DENTIGRAMA_WARNING: Paciente con ID {patient_id} no encontrado.")
            else:
                old_dentigrama_url = patient.dentigrama_canvas

        # Generar public_id único
        base_public_id = f"dentigrama_patient_{patient_id}" if patient_id else "dentigrama_temp_session"
        new_public_id = f"{base_public_id}_{uuid.uuid4().hex}"

        current_app.logger.info(f"UPLOAD_DENTIGRAMA_INFO: Subiendo dentigrama para paciente {patient_id or 'temporal'}")

        upload_result = cloudinary.uploader.upload(
            image_data,
            folder="dentigramas",
            public_id=new_public_id
        )
        new_cloudinary_url = upload_result.get('secure_url')

        if not new_cloudinary_url:
            current_app.logger.error(f"UPLOAD_DENTIGRAMA_ERROR: Falló la subida a Cloudinary")
            return {'success': False, 'message': 'Error al subir el dentigrama a Cloudinary.'}

        # Actualizar BD si hay paciente
        if patient:
            if old_dentigrama_url:
                delete_from_cloudinary(old_dentigrama_url)
            patient.dentigrama_canvas = new_cloudinary_url
            db.session.commit()
            current_app.logger.info(f"UPLOAD_DENTIGRAMA_INFO: Dentigrama actualizado en BD para paciente {patient_id}")

        return {'success': True, 'url': new_cloudinary_url, 'message': 'Dentigrama subido exitosamente'}

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"UPLOAD_DENTIGRAMA_FATAL_ERROR: {e}", exc_info=True)
        return {'success': False, 'message': 'Ocurrió un error inesperado al subir el dentigrama.'}
