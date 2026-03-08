# clinica/utils.py

import os
import calendar
import locale
from datetime import date, datetime, time
from sqlalchemy import func, case, or_, and_
from sqlalchemy.orm import joinedload
from .extensions import db
from .models import Paciente, Cita
from flask import current_app
from flask_login import current_user

import logging
logger = logging.getLogger(__name__)

nombres_meses = [calendar.month_name[i] for i in range(1, 13)]

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def eliminar_imagen(ruta_imagen_relativa):
    if not ruta_imagen_relativa:
        return
    try:
        ruta_absoluta = os.path.join(current_app.static_folder, ruta_imagen_relativa)
        if os.path.exists(ruta_absoluta):
            os.remove(ruta_absoluta)
            current_app.logger.info(f"Archivo eliminado exitosamente: {ruta_absoluta}")
        else:
            current_app.logger.warning(f"Se intentó eliminar un archivo que no existe: {ruta_absoluta}")
    except Exception as e:
        current_app.logger.error(f"Error crítico al eliminar imagen {ruta_imagen_relativa}: {e}", exc_info=True)

def convertir_a_fecha(valor_str):
    if not valor_str or not isinstance(valor_str, str):
        return None
    try:
        return datetime.strptime(valor_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None

# --- FUNCIÓN get_index_panel_data OPTIMIZADA (SIN CAMPOS INNECESARIOS) ---
def get_index_panel_data(today_date: date, current_time: time):
    """Función optimizada para obtener los datos necesarios para el panel de inicio."""
    from sqlalchemy.orm import load_only, joinedload
    from sqlalchemy import or_, and_
    import locale
    
    datos_panel = {}
    
    # --- CONSULTA BASE PARA CITAS (SOLO IDs para conteos) ---
    # Primero obtenemos solo los IDs de las citas de hoy para filtrar después
    citas_hoy_ids_query = db.session.query(Cita.id).filter(
        Cita.fecha == today_date,
        Cita.is_deleted == False
    )
    
    # Filtrar por permisos
    if hasattr(current_user, 'is_admin') and not current_user.is_admin:
        citas_hoy_ids_query = citas_hoy_ids_query.outerjoin(Paciente, Cita.paciente_id == Paciente.id).filter(
            or_(
                Paciente.odontologo_id == current_user.id,
                Cita.paciente_id == None
            )
        )
    
    # 2. Estadísticas: Citas de hoy (conteo rápido)
    citas_hoy_count = citas_hoy_ids_query.count()
    datos_panel['estadisticas'] = {'citas_hoy': citas_hoy_count or 0}
    
    # 3. Próxima cita (OPTIMIZADA - SOLO CAMPOS NECESARIOS)
    proxima_cita_query = Cita.query.options(
        load_only(
            Cita.id, 
            Cita.fecha, 
            Cita.hora, 
            Cita.motivo,
            Cita.paciente_id,
            Cita.paciente_nombres_str,
            Cita.paciente_apellidos_str
        )
    ).filter(
        or_(
            Cita.fecha > today_date,
            and_(Cita.fecha == today_date, Cita.hora >= current_time)
        ),
        Cita.is_deleted == False
    )
    
    # Filtrar por permisos
    if hasattr(current_user, 'is_admin') and not current_user.is_admin:
        proxima_cita_query = proxima_cita_query.outerjoin(Paciente, Cita.paciente_id == Paciente.id).filter(
            or_(
                Paciente.odontologo_id == current_user.id,
                Cita.paciente_id == None
            )
        )
    
    proxima_cita_obj = proxima_cita_query.order_by(Cita.fecha, Cita.hora).first()
    
    proxima_cita_data = None
    if proxima_cita_obj:
        # Formatear fecha
        fecha_cita_str_buffer = proxima_cita_obj.fecha.strftime("%d %b, %Y")
        hora_cita_str = proxima_cita_obj.hora.strftime("%I:%M %p")
        
        # Obtener nombre del paciente (sin cargar todo el objeto)
        paciente_nombre_proxima_cita = "Paciente sin registrar"
        if proxima_cita_obj.paciente_id:
            # Cargar SOLO el nombre del paciente si existe
            paciente = db.session.query(Paciente).options(
                load_only(Paciente.nombres, Paciente.apellidos)
            ).get(proxima_cita_obj.paciente_id)
            if paciente and not paciente.is_deleted:
                paciente_nombre_proxima_cita = f"{paciente.nombres} {paciente.apellidos}"
        elif proxima_cita_obj.paciente_nombres_str:
            paciente_nombre_proxima_cita = f"{proxima_cita_obj.paciente_nombres_str} {proxima_cita_obj.paciente_apellidos_str or ''}".strip()
        
        proxima_cita_data = {
            'fecha_formateada': f"{fecha_cita_str_buffer} a las {hora_cita_str}",
            'paciente_nombre': paciente_nombre_proxima_cita,
            'motivo': proxima_cita_obj.motivo or "No especificado"
        }
    datos_panel['proxima_cita'] = proxima_cita_data
    
    # 5. Lista de citas de hoy (OPTIMIZADA)
    citas_de_hoy_lista_query = Cita.query.options(
        load_only(
            Cita.id,
            Cita.hora,
            Cita.motivo,
            Cita.doctor,
            Cita.estado,
            Cita.paciente_id,
            Cita.paciente_nombres_str,
            Cita.paciente_apellidos_str
        )
    ).filter(
        Cita.fecha == today_date,
        Cita.is_deleted == False
    )
    
    # Filtrar por permisos
    if hasattr(current_user, 'is_admin') and not current_user.is_admin:
        citas_de_hoy_lista_query = citas_de_hoy_lista_query.outerjoin(Paciente, Cita.paciente_id == Paciente.id).filter(
            or_(
                Paciente.odontologo_id == current_user.id,
                Cita.paciente_id == None
            )
        )
    
    citas_de_hoy_lista = citas_de_hoy_lista_query.order_by(Cita.hora).all()
    
    # Recopilar IDs de pacientes para carga eficiente
    paciente_ids = list(set([c.paciente_id for c in citas_de_hoy_lista if c.paciente_id]))
    pacientes_dict = {}
    if paciente_ids:
        pacientes = db.session.query(Paciente).options(
            load_only(Paciente.id, Paciente.nombres, Paciente.apellidos, Paciente.is_deleted)
        ).filter(Paciente.id.in_(paciente_ids)).all()
        for p in pacientes:
            pacientes_dict[p.id] = p
    
    citas_hoy_procesadas = []
    for cita_item in citas_de_hoy_lista:
        paciente_nombre_completo = "Paciente sin registrar"
        
        if cita_item.paciente_id and cita_item.paciente_id in pacientes_dict:
            paciente = pacientes_dict[cita_item.paciente_id]
            if not paciente.is_deleted:
                paciente_nombre_completo = f"{paciente.nombres} {paciente.apellidos}"
        elif cita_item.paciente_nombres_str:
            paciente_nombre_completo = f"{cita_item.paciente_nombres_str} {cita_item.paciente_apellidos_str or ''}".strip()
        
        citas_hoy_procesadas.append({
            'id': cita_item.id,
            'hora_formateada': cita_item.hora.strftime("%I:%M %p"),
            'paciente_nombre_completo': paciente_nombre_completo,
            'motivo': cita_item.motivo,
            'doctor': cita_item.doctor,
            'estado': cita_item.estado,
        })
    
    datos_panel['citas_del_dia'] = citas_hoy_procesadas
    
    return datos_panel
# --- VERSIÓN MEJORADA DE extract_public_id_from_url (se mantiene igual) ---
def extract_public_id_from_url(url):
    """
    Extrae el public_id de una URL de Cloudinary de forma robusta.
    Ejemplos de URLs de Cloudinary:
    https://res.cloudinary.com/mi-cloud/image/upload/v1678901234/folder/subfolder/public_id.png
    https://res.cloudinary.com/mi-cloud/image/upload/folder/subfolder/public_id.png
    """
    if not isinstance(url, str) or not url: # Comprobar que es string y no vacío
        return None
    try:
        # Dividir la URL por la parte '/upload/' para obtener lo que viene después
        parts = url.split('/upload/')
        if len(parts) < 2:
            logger.warning(f"URL de Cloudinary inválida (no contiene '/upload/'): {url}")
            return None

        path_with_version_and_ext = parts[1] # Esto podría ser "v1234567890/folder/public_id.png" o "folder/public_id.png"

        # Eliminar el componente de versión (ej. v1234567890) si existe
        path_components = path_with_version_and_ext.split('/')
        if path_components[0].startswith('v') and path_components[0][1:].isdigit():
            # Si el primer componente es una versión numérica, lo saltamos
            public_id_parts = path_components[1:]
        else:
            public_id_parts = path_components

        # Unir las partes restantes y quitar la extensión del archivo
        full_public_id_with_ext = '/'.join(public_id_parts)
        public_id = os.path.splitext(full_public_id_with_ext)[0] # os.path.splitext es robusto para quitar extensiones

        # Cloudinary espera el public_id incluyendo las carpetas
        # Por ejemplo, si la URL es ".../dentigramas_pacientes/mi_dentigrama.png"
        # el public_id debería ser "dentigramas_pacientes/mi_dentigrama"

        # Asegúrate de que el public_id no esté vacío después del procesamiento
        if not public_id:
            logger.warning(f"Public ID extraído está vacío de la URL: {url}")
            return None

        return public_id

    except (ValueError, IndexError, TypeError) as e:
        logger.warning(f"Error al extraer el public_id de la URL '{url}'. Error: {e}", exc_info=True)
        return None
    



# clinica/utils.py

# ... (tus imports y funciones existentes) ...

# Función auxiliar para borrar archivos de Cloudinary
def delete_from_cloudinary(url):
    """Borra un recurso de Cloudinary dada su URL."""
    if url:
        public_id = extract_public_id_from_url(url)
        current_app.logger.debug(f"CLOUDINARY_DELETE_DEBUG: Intentando borrar URL: {url}, Public ID extraído: {public_id}") # <-- NUEVO LOG
        if public_id:
            try:
                result = cloudinary.uploader.destroy(public_id) # Captura el resultado de la destrucción
                current_app.logger.debug(f"CLOUDINARY_DELETE_DEBUG: Resultado de Cloudinary.destroy para {public_id}: {result}") # <-- NUEVO LOG

                # Cloudinary devuelve un diccionario, y "result":"ok" es el éxito.
                if result and result.get("result") == "ok":
                    current_app.logger.info(f"CLOUDINARY: Recurso {public_id} eliminado exitosamente.")
                    return True
                else:
                    # Si no es "ok", es un fallo o un error diferente.
                    error_message = result.get("error", {}).get("message", "Mensaje de error no disponible") if result and "error" in result else "Error desconocido"
                    current_app.logger.warning(f"CLOUDINARY: Fallo al eliminar recurso {public_id} de Cloudinary. Resultado: {result}. Error: {error_message}") # <-- MEJOR LOG
                    return False
            except Exception as e:
                current_app.logger.error(f"CLOUDINARY_DELETE_ERROR: Excepción al intentar eliminar recurso {public_id} de Cloudinary: {e}", exc_info=True) # <-- LOG MÁS ESPECÍFICO
                return False
        else:
            current_app.logger.warning(f"CLOUDINARY_DELETE_WARNING: No se pudo extraer public_id de la URL: {url}. No se intentó eliminar.") # <-- NUEVO LOG
            return False # No hay public_id para borrar
    current_app.logger.debug("CLOUDINARY_DELETE_DEBUG: URL de imagen vacía o None, no hay nada que borrar.") # <-- NUEVO LOG
    return False # La URL estaba vacía




# clinica/utils.py (AGREGAR ESTA FUNCIÓN)

def get_transformed_profile_image_url(original_url):
    """
    Inserta la transformación de Cloudinary para forzar el tamaño y formato (JPEG),
    permitiendo que los PDFs se muestren como miniaturas de imagen.
    
    Transformación: f_jpg,w_120,h_120,c_fill (Formato JPG, 120x120, Crop/Fill)
    """
    if not original_url or '/upload/' not in original_url:
        # Retorna la URL si está vacía o si no es de Cloudinary (por ejemplo, el placeholder)
        return original_url

    # Cloudinary usa 'f_jpg' para forzar la conversión a JPG, lo que genera la miniatura del PDF.
    TRANSFORMATION = 'f_jpg,q_auto:eco,fl_progressive,w_200,h_120,c_fit'
    
    # Dividir la URL en la parte de 'upload' e insertar la transformación
    parts = original_url.split('/upload/', 1)
    
    if len(parts) == 2:
        # URL formateada: base_url/upload/TRANSFORMACION/path_del_recurso
        return f"{parts[0]}/upload/{TRANSFORMATION}/{parts[1]}"
        
    return original_url