# clinica/utils.py

import os
import calendar
import locale
from datetime import date, datetime, time
from sqlalchemy import func, case, or_, and_ # Asegúrate de que 'and_' esté importado
from sqlalchemy.orm import joinedload
from .extensions import db
from .models import Paciente, Cita
from flask import current_app
from flask_login import current_user

import logging
logger = logging.getLogger(__name__)

nombres_meses = [calendar.month_name[i] for i in range(1, 13)]

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

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

def get_index_panel_data(today_date: date, current_time: time):
    """Función para obtener los datos necesarios para el panel de inicio."""
    datos_panel = {}

    # 1. Fecha actual formateada (¡ahora usa today_date!)
    # ESTA SECCIÓN DE CÓDIGO YA NO ES NECESARIA AQUÍ.
    # La fecha formateada principal y la corta ahora se gestionan en main.py
    # y se pasan directamente al render_template, para evitar este conflicto.
    # Puedes eliminar todo el bloque 'locale' y 'fecha_formateada_buffer' de aquí.
    # Si aún necesitas formatear fechas cortas para otras partes DENTRO de get_index_panel_data
    # que no sean la fecha principal del dashboard, puedes mantener una variable local,
    # pero NO la añadas a datos_panel['fecha_actual_formateada'] ni a datos_panel['fecha_actual_corta'].
    
    # Para simplificar y evitar el conflicto, simplemente asegurémonos de que NO estamos
    # añadiendo 'fecha_actual_corta' ni 'fecha_actual_formateada' a 'datos_panel'.
    # Si quieres una fecha corta para Citas para Hoy (XX noviembre), puedes dejarla localmente.

    # --- CONSULTA BASE PARA CITAS DEL DASHBOARD ---
    base_query_citas = Cita.query.outerjoin(Paciente, Cita.paciente_id == Paciente.id).filter(
        Cita.is_deleted == False
    )

    if hasattr(current_user, 'is_admin') and not current_user.is_admin:
        base_query_citas = base_query_citas.filter(
            or_(
                Paciente.odontologo_id == current_user.id,
                Cita.paciente_id == None
            )
        )

    # 2. Estadísticas: Citas de hoy
    citas_hoy_count = base_query_citas.filter(Cita.fecha == today_date).count()
    datos_panel['estadisticas'] = {'citas_hoy': citas_hoy_count or 0}

    # 3. Próxima cita
    proxima_cita_obj = base_query_citas.filter(
        or_(
            Cita.fecha > today_date,
            and_(Cita.fecha == today_date, Cita.hora >= current_time)
        )
    ).options(joinedload(Cita.paciente))\
     .order_by(Cita.fecha, Cita.hora)\
     .first()

    proxima_cita_data = None
    if proxima_cita_obj:
        # Asegúrate de que el formateo de fecha para la próxima cita sea consistente y use today_date si aplica
        # O si es una fecha futura, solo formatear la fecha del objeto cita
        
        # Guardamos el locale original antes de cambiarlo
        locale_original_time = locale.getlocale(locale.LC_TIME)
        try:
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
            fecha_cita_str_buffer = proxima_cita_obj.fecha.strftime("%d %b, %Y")
        except locale.Error:
            logger.warning("Locale 'es_ES.UTF-8' no disponible. Usando locale por defecto.")
            locale.setlocale(locale.LC_TIME, '')
            fecha_cita_str_buffer = proxima_cita_obj.fecha.strftime("%d %b, %Y")
        finally:
            # Restaurar el locale original
            if locale_original_time != (None, None):
                try:
                    locale.setlocale(locale.LC_TIME, locale_original_time)
                except locale.Error:
                    logger.warning(f"Advertencia: No se pudo restaurar el locale original {locale_original_time} para LC_TIME.")

        hora_cita_str = proxima_cita_obj.hora.strftime("%I:%M %p")

        paciente_nombre_proxima_cita = "Paciente sin registrar"
        if proxima_cita_obj.paciente and not proxima_cita_obj.paciente.is_deleted:
            paciente_nombre_proxima_cita = f"{proxima_cita_obj.paciente.nombres} {proxima_cita_obj.paciente.apellidos}"
        elif proxima_cita_obj.paciente_nombres_str and proxima_cita_obj.paciente_apellidos_str:
            paciente_nombre_proxima_cita = f"{proxima_cita_obj.paciente_nombres_str} {proxima_cita_obj.paciente_apellidos_str}"
        elif proxima_cita_obj.paciente_nombres_str:
            paciente_nombre_proxima_cita = proxima_cita_obj.paciente_nombres_str

        proxima_cita_data = {
            'fecha_formateada': f"{fecha_cita_str_buffer} a las {hora_cita_str}",
            'paciente_nombre': paciente_nombre_proxima_cita,
            'motivo': proxima_cita_obj.motivo or "No especificado"
        }
    datos_panel['proxima_cita'] = proxima_cita_data

    # 4. Fecha actual corta (¡Gestionada en main.py, NO la añadas a datos_panel aquí!)
    # Este bloque de código para 'fecha_corta_buffer' debe ELIMINARSE COMPLETAMENTE o
    # asegurarse de que NO ASIGNE a datos_panel['fecha_actual_corta'].
    # Si necesitas una fecha corta para algún propósito interno de get_index_panel_data,
    # puedes mantener la lógica localmente, pero no la exportes en 'datos_panel'.
    # Ejemplo de eliminación segura (opcional si la variable no se usa más):
    # try:
    #     locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    #     _temp_fecha_corta_para_uso_interno = today_date.strftime("%d de %B").capitalize()
    # except locale.Error:
    #     _temp_fecha_corta_para_uso_interno = today_date.strftime("%d %B").capitalize()
    # finally:
    #     if locale_original_time != (None, None):
    #         try:
    #             locale.setlocale(locale.LC_TIME, locale_original_time)
    #         except locale.Error: pass


    # 5. Lista de citas de hoy
    citas_de_hoy_lista_query = base_query_citas.filter(Cita.fecha == today_date)
    citas_de_hoy_lista = citas_de_hoy_lista_query.options(joinedload(Cita.paciente))\
                                                .order_by(Cita.hora)\
                                                .all()

    citas_hoy_procesadas = []
    for cita_item in citas_de_hoy_lista:
        paciente_nombre_completo = "Paciente sin registrar"
        if cita_item.paciente and not cita_item.paciente.is_deleted:
            paciente_nombre_completo = f"{cita_item.paciente.nombres} {cita_item.paciente.apellidos}"
        elif cita_item.paciente_nombres_str and cita_item.paciente_apellidos_str:
            paciente_nombre_completo = f"{cita_item.paciente_nombres_str} {cita_item.paciente_apellidos_str}"
        elif cita_item.paciente_nombres_str:
            paciente_nombre_completo = cita_item.paciente_nombres_str

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


# --- VERSIÓN MEJORADA DE extract_public_id_from_url ---
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