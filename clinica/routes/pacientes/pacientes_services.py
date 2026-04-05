
import os
import uuid
from datetime import datetime, date
import cloudinary
import cloudinary.uploader
import pytz
from flask import request, jsonify, flash, current_app
from sqlalchemy import or_
from sqlalchemy.orm import load_only
from ...extensions import db
from ...models import Paciente, Cita, Evolucion, AuditLog
from ...utils import allowed_file, convertir_a_fecha, extract_public_id_from_url
from clinica.campos_activos import load_only_paciente_activo, load_only_evolucion_activo
from clinica.services.plan_service import PlanService # Agrega esta línea arriba
# =========================================================================
# === FUNCIONES AUXILIARES PARA CLOUDINARY ===
# =========================================================================

def upload_file_to_cloudinary(file, folder_name="general_uploads"):
    """Sube un objeto FileStorage a Cloudinary y devuelve su URL segura."""
    if not file or file.filename == '': return None
    if not allowed_file(file.filename): return None

    try:
        file.seek(0)
        upload_result = cloudinary.uploader.upload(file, folder=folder_name)
        return upload_result.get('secure_url')
    except Exception as e:
        current_app.logger.error(f"CLOUDINARY ERROR: {str(e)}", exc_info=True)
        return None


def upload_base64_dentigrama(base64_string, patient_id, specific_public_id=None):
    """Sube dentigrama evitando subir URLs y gestionando nombres fijos."""
    if not base64_string: return None
    
    # --- CORRECCIÓN CRÍTICA: Si ya es una URL, NO SUBIR NADA ---
    if base64_string.startswith('http'): 
        return base64_string 

    if base64_string.startswith('data:image'):
        try:
            # SIEMPRE usar el mismo public_id basado en el ID del paciente
            if patient_id and str(patient_id) != "new_patient":
                # Importante: NO incluir la carpeta aquí, Cloudinary la añadirá
                public_id = f"dentigrama_paciente_{patient_id}"
            else:
                public_id = specific_public_id or f"temp_dentigrama_{uuid.uuid4().hex}"

            # ANTES de subir, eliminar cualquier versión anterior con ESTE MISMO public_id
            # para asegurar sobrescritura limpia
            try:
                cloudinary.uploader.destroy(f"dentigramas_pacientes/{public_id}", invalidate=True)
            except:
                pass  # Si no existe, ignorar

            # Subir con overwrite=True y invalidate=True
            upload_result = cloudinary.uploader.upload(
                base64_string,
                folder="dentigramas_pacientes",
                public_id=public_id,  # Cloudinary combinará folder + public_id
                overwrite=True,
                invalidate=True,
                resource_type="image"
            )
            
            if upload_result and upload_result.get('secure_url'):
                return upload_result.get('secure_url')
            else:
                return None
                
        except Exception as e:
            current_app.logger.error(f"DENTIGRAMA ERROR: {e}")
            return None
    return None

def delete_from_cloudinary(url):
    """Borra un recurso de Cloudinary dada su URL."""
    if url and 'cloudinary.com' in url:
        public_id = extract_public_id_from_url(url)
        if public_id:
            try:
                cloudinary.uploader.destroy(public_id)
                return True
            except Exception as e:
                current_app.logger.error(f"Error al eliminar recurso Cloudinary: {e}")
                return False
    return False


def eliminar_imagenes_paciente(paciente, log_prefix="PACIENTE"):
    """Elimina todas las imágenes de un paciente de Cloudinary."""
    imagenes = []
    
    # Solo agregar URLs que existan en el modelo actual
    if hasattr(paciente, 'imagen_perfil_url') and paciente.imagen_perfil_url:
        imagenes.append(paciente.imagen_perfil_url)
    
    if hasattr(paciente, 'dentigrama_canvas') and paciente.dentigrama_canvas:
        imagenes.append(paciente.dentigrama_canvas)
    
    for url in imagenes:
        delete_from_cloudinary(url)


# =========================================================================
# === SERVICIOS DE LÓGICA DE NEGOCIO ===
# =========================================================================

def listar_pacientes_service(usuario, page, search_term):
    """Lista pacientes con solo los campos necesarios para la UI"""
    query = db.session.query(Paciente).options(
        load_only_paciente_activo()
    ).filter(Paciente.is_deleted == False)

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
    
    return query.order_by(Paciente.id.desc()).paginate(page=page, per_page=7, error_out=False)

def obtener_paciente_service(paciente_id, usuario):
    """Obtiene un paciente con SOLO los campos necesarios, unificando nombres"""
    # 1. Buscar paciente con campos optimizados
    query = db.session.query(Paciente).filter_by(id=paciente_id, is_deleted=False)
    # .options(load_only_paciente_activo())  # ← Comentado temporalmente
    
    if not usuario.is_admin:
        query = query.filter_by(odontologo_id=usuario.id)
    paciente = query.first_or_404()

    # 2. Cargar evoluciones por separado (optimizado)
    evoluciones = db.session.query(Evolucion).options(
        load_only_evolucion_activo()
    ).filter(
        Evolucion.paciente_id == paciente_id
    ).order_by(Evolucion.fecha.desc()).all()

    # 3. Procesar evoluciones para el template
    evoluciones_procesadas = []
    for evo in evoluciones:
        fecha_formateada = "N/A"
        if isinstance(evo.fecha, (date, datetime)):
            try:
                fecha_formateada = evo.fecha.strftime('%d de %B, %Y')
            except:
                fecha_formateada = evo.fecha.strftime('%d/%m/%Y')
        
        evoluciones_procesadas.append({
            'id': evo.id,
            'descripcion': evo.descripcion,
            'fecha_formateada': fecha_formateada
        })

    # 4. Construir diccionario UNIFICADO (Sin campos RIPS de nombres)
    paciente_data = {
        # Datos básicos (Ahora unificados)
        'id': paciente.id,
        'nombres': paciente.nombres or '',
        'apellidos': paciente.apellidos or '',
        
        # Identificación y contacto
        'tipo_documento': paciente.tipo_documento or '',
        'documento': paciente.documento or '',
        'telefono': paciente.telefono or '',
        'email': paciente.email or '',
        'fecha_nacimiento': paciente.fecha_nacimiento.strftime('%d/%m/%Y') if paciente.fecha_nacimiento else '',
        'edad': f"{paciente.edad} años" if paciente.edad else '',
        'direccion': paciente.direccion or '',
        'barrio': paciente.barrio or '',
        
        # Información clínica (Mantenemos todos los campos)
        'alergias': paciente.alergias or '',
        'motivo_consulta': paciente.motivo_consulta or '',
        'enfermedad_actual': paciente.enfermedad_actual or '',
        'observaciones': paciente.observaciones or '',
        
        # Multimedia
        'dentigrama_canvas': paciente.dentigrama_canvas,
        'imagen_perfil_url': paciente.imagen_perfil_url
    }

    # 5. Obtener public_id del dentigrama si existe para trazos
    full_public_id_trazos = None
    if paciente.dentigrama_canvas:
        try:
            full_public_id_trazos = extract_public_id_from_url(paciente.dentigrama_canvas)
        except:
            pass

    return paciente_data, evoluciones_procesadas, full_public_id_trazos


def editar_paciente_service(paciente_id, form_data, files, usuario):
    # Buscar paciente asegurando permisos
    query = Paciente.query.filter_by(id=paciente_id, is_deleted=False)
    if not usuario.is_admin:
        query = query.filter_by(odontologo_id=usuario.id)
    paciente = query.first_or_404()
    
    try:
        # ==============================================================================
        # 1. DATOS BÁSICOS (UNIFICADOS)
        # ==============================================================================
        # Ahora tomamos directamente los nombres y apellidos del nuevo formulario
        paciente.nombres = form_data.get('nombres', '').strip()
        paciente.apellidos = form_data.get('apellidos', '').strip()
        
        # Eliminamos la fragmentación de nombres RIPS y la concatenación manual
        paciente.tipo_documento = form_data.get('tipo_documento')
        paciente.documento = form_data.get('documento')
        paciente.email = form_data.get('email')
        paciente.fecha_nacimiento = convertir_a_fecha(form_data.get('fecha_nacimiento', ''))
        paciente.edad = form_data.get('edad', type=int)
        paciente.telefono = form_data.get('telefono')
        paciente.direccion = form_data.get('direccion')
        paciente.barrio = form_data.get('barrio')

        # ==============================================================================
        # 3. DATOS CLÍNICOS (MANTENIDOS)
        # ==============================================================================
        paciente.motivo_consulta = form_data.get('motivo_consulta')
        paciente.enfermedad_actual = form_data.get('enfermedad_actual')
        paciente.alergias = form_data.get('alergias')
        paciente.observaciones = form_data.get('observaciones')

        # ==============================================================================
        # 4. GESTIÓN DE IMAGEN DE PERFIL
        # ==============================================================================
        if form_data.get('eliminar_imagen_perfil') == 'true':
            delete_from_cloudinary(paciente.imagen_perfil_url)
            paciente.imagen_perfil_url = None

        if 'imagen_perfil' in files and files['imagen_perfil'].filename != '':
             nueva_url = upload_file_to_cloudinary(files['imagen_perfil'], "pacientes_perfil")
             if nueva_url:
                 # Borrar la anterior antes de asignar la nueva para ahorrar espacio
                 if paciente.imagen_perfil_url: 
                     delete_from_cloudinary(paciente.imagen_perfil_url)
                 paciente.imagen_perfil_url = nueva_url

        # ==============================================================================
        # 5. GESTIÓN DEL DENTIGRAMA (LÓGICA ORIGINAL PROTEGIDA)
        # ==============================================================================
        raw_dentigrama = form_data.get('dentigrama_url') or form_data.get('dentigrama_canvas')
        
        if raw_dentigrama:
            # Subimos usando el ID del paciente. 
            # Cloudinary SOBREESCRIBE el archivo existente al usar el mismo public_id.
            nueva_url = upload_base64_dentigrama(raw_dentigrama, paciente.id)
            
            if nueva_url:
                # ⚠️ IMPORTANTE: Mantenemos tu corrección de NO borrar 'paciente.dentigrama_canvas' 
                # antiguo aquí para evitar eliminar por error lo que Cloudinary acaba de actualizar.
                paciente.dentigrama_canvas = nueva_url

        db.session.commit()
        return {'success': True, 'message': 'Paciente actualizado correctamente'}

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error al editar paciente {paciente_id}: {e}', exc_info=True)
        return {'success': False, 'message': f'Error al actualizar el paciente: {str(e)}'}
    

def borrar_paciente_service(paciente_id, usuario):
    query = Paciente.query.filter_by(id=paciente_id)
    if not usuario.is_admin:
        query = query.filter_by(odontologo_id=usuario.id)
    paciente = query.first_or_404()
    
    if paciente.is_deleted:
        return {'success': False, 'message': f"El paciente '{paciente.nombres} {paciente.apellidos}' ya se encuentra en la papelera."}

    paciente_nombre_completo = f"{paciente.nombres} {paciente.apellidos}"
    
    try:
        current_app.logger.info(f"PACIENTE_BORRADO: Iniciando eliminación de imágenes para paciente ID {paciente.id}")
        eliminar_imagenes_paciente(paciente, log_prefix="PACIENTE_BORRADO")
        
        paciente.is_deleted = True
        paciente.deleted_at = datetime.utcnow()

        citas_del_paciente = Cita.query.filter_by(paciente_id=paciente.id, is_deleted=False).all()
        for cita_item in citas_del_paciente:
            cita_item.is_deleted = True
            cita_item.deleted_at = datetime.utcnow()

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



def crear_paciente_service(form_data, files, usuario):

    try:

        # Crear nueva instancia de Paciente
        nuevo_paciente = Paciente()
        # Asignar odontólogo actual
        nuevo_paciente.odontologo_id = usuario.id
        
        # ==============================================================================
        # 1. DATOS BÁSICOS (UNIFICADOS)
        # ==============================================================================
        # Ahora capturamos directamente los nombres y apellidos unificados
        nuevo_paciente.nombres = form_data.get('nombres', '').strip()
        nuevo_paciente.apellidos = form_data.get('apellidos', '').strip()
        
        nuevo_paciente.tipo_documento = form_data.get('tipo_documento')
        nuevo_paciente.documento = form_data.get('documento')
        nuevo_paciente.email = form_data.get('email')
        nuevo_paciente.fecha_nacimiento = convertir_a_fecha(form_data.get('fecha_nacimiento', ''))
        nuevo_paciente.edad = form_data.get('edad', type=int)
        nuevo_paciente.telefono = form_data.get('telefono')
        nuevo_paciente.direccion = form_data.get('direccion')
        nuevo_paciente.barrio = form_data.get('barrio')
        
        # ==============================================================================
        # 2. INFORMACIÓN CLÍNICA SIMPLE (MANTENIDA)
        # ==============================================================================
        nuevo_paciente.alergias = form_data.get('alergias')
        nuevo_paciente.motivo_consulta = form_data.get('motivo_consulta')
        nuevo_paciente.enfermedad_actual = form_data.get('enfermedad_actual')
        nuevo_paciente.observaciones = form_data.get('observaciones')
        
        # ==============================================================================
        # 3. GESTIÓN DE IMAGEN DE PERFIL
        # ==============================================================================
        if 'imagen_perfil' in files and files['imagen_perfil'].filename != '':
            nueva_url = upload_file_to_cloudinary(files['imagen_perfil'], "pacientes_perfil")
            if nueva_url:
                nuevo_paciente.imagen_perfil_url = nueva_url

        # Guardar en base de datos para obtener el ID necesario para el dentigrama
        db.session.add(nuevo_paciente)
        db.session.commit()

        # 🔥 MANTENIDO: Incrementar el contador de pacientes del día para el SaaS
        PlanService.incrementar_contador_paciente(usuario.id)
        
        # ==============================================================================
        # 4. DENTIGRAMA (MANTENIENDO TU LÓGICA DE LIMPIEZA EXPLÍCITA)
        # ==============================================================================
        raw_dentigrama = form_data.get('dentigrama_url') or form_data.get('dentigrama_canvas')
        if raw_dentigrama:
            # Tu lógica original: Eliminar explícitamente cualquier dentigrama previo 
            # vinculado a este ID de paciente en Cloudinary antes de subir el nuevo.
            public_id_previo = f"dentigramas_pacientes/dentigrama_paciente_{nuevo_paciente.id}"
            try:
                resultado = cloudinary.uploader.destroy(public_id_previo, invalidate=True)
                current_app.logger.info(f"Limpieza previa al crear: {public_id_previo} - Resultado: {resultado}")
            except Exception as e:
                current_app.logger.warning(f"No se pudo eliminar dentigrama previo: {e}")
                pass
            
            nueva_url = upload_base64_dentigrama(raw_dentigrama, nuevo_paciente.id)
            if nueva_url:
                nuevo_paciente.dentigrama_canvas = nueva_url
                db.session.commit()
            else:
                current_app.logger.warning(f"No se pudo subir el dentigrama para el paciente {nuevo_paciente.id}")

        return {
            'success': True, 
            'message': 'Paciente creado correctamente',
            'paciente_id': nuevo_paciente.id
        }
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error al crear paciente: {e}', exc_info=True)
        return {'success': False, 'message': f'Error al crear el paciente: {str(e)}'}
