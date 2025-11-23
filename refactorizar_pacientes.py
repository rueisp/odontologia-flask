#!/usr/bin/env python3
"""
Script para refactorizar pacientes.py de forma segura
Aplica las correcciones identificadas en el análisis
"""

import re
import shutil
from pathlib import Path

def refactorizar_pacientes():
    """Aplica todas las correcciones al archivo pacientes.py"""
    
    archivo = Path("clinica/routes/pacientes.py")
    
    # Crear backup
    backup = archivo.with_suffix('.py.backup')
    shutil.copy(archivo, backup)
    print(f"✅ Backup creado: {backup}")
    
    # Leer contenido
    contenido = archivo.read_text(encoding='utf-8')
    contenido_original = contenido
    
    # ========================================
    # CORRECCIÓN 1: Eliminar función convertir_a_fecha duplicada (líneas 22-30)
    # ========================================
    patron_funcion_duplicada = r'# Función auxiliar para convertir string a fecha \r?\ndef convertir_a_fecha\(fecha_str\):.*?return None\r?\n\r?\n'
    contenido = re.sub(patron_funcion_duplicada, '', contenido, flags=re.DOTALL)
    print("✅ Eliminada función convertir_a_fecha duplicada")
    
    # ========================================
    # CORRECCIÓN 2: Reemplazar print() con current_app.logger.debug()
    # ========================================
    # Línea 112-113
    contenido = contenido.replace(
        'print(f"Usuario: {current_user.username}, es admin: {current_user.is_admin}")',
        'current_app.logger.debug(f"Usuario: {current_user.username}, es admin: {current_user.is_admin}")'
    )
    contenido = contenido.replace(
        'print(f"Pacientes encontrados para este usuario: {pacientes.total}")',
        'current_app.logger.debug(f"Pacientes encontrados para este usuario: {pacientes.total}")'
    )
    # Línea 219
    contenido = contenido.replace(
        'print(f"DENTIGRAMA ERROR (Backend): Error al extraer public ID de dentigrama_canvas: {e}")',
        'current_app.logger.error(f"DENTIGRAMA ERROR (Backend): Error al extraer public ID de dentigrama_canvas: {e}")'
    )
    print("✅ Reemplazados print() con current_app.logger")
    
    # ========================================
    # CORRECCIÓN 3: Eliminar función get_logger() y código relacionado (líneas 697-717)
    # ========================================
    patron_get_logger = r'# Función para obtener el logger.*?Paciente = None\r?\n'
    contenido = re.sub(patron_get_logger, '', contenido, flags=re.DOTALL)
    print("✅ Eliminada función get_logger() y reimportaciones innecesarias")
    
    # ========================================
    # CORRECCIÓN 4: Agregar función auxiliar para procesar subida de imágenes
    # ========================================
    funcion_procesar_imagen = '''
def procesar_subida_imagen(file_key, folder_name, is_ajax=False):
    """Procesa la subida de una imagen desde request.files
    
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
    """Elimina todas las imágenes de un paciente de Cloudinary
    
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

'''
    
    # Insertar las nuevas funciones después de delete_from_cloudinary
    patron_insercion = r'(# =========================================================================\r?\n# === FIN FUNCIONES AUXILIARES ===\r?\n# =========================================================================)'
    contenido = re.sub(
        patron_insercion,
        funcion_procesar_imagen + r'\1',
        contenido
    )
    print("✅ Agregadas funciones auxiliares procesar_subida_imagen() y eliminar_imagenes_paciente()")
    
    # Guardar cambios
    archivo.write_text(contenido, encoding='utf-8')
    
    # Mostrar estadísticas
    lineas_antes = len(contenido_original.splitlines())
    lineas_despues = len(contenido.splitlines())
    reduccion = lineas_antes - lineas_despues
    
    print(f"\n📊 Estadísticas:")
    print(f"   Líneas antes: {lineas_antes}")
    print(f"   Líneas después: {lineas_despues}")
    print(f"   Reducción: {reduccion} líneas ({reduccion/lineas_antes*100:.1f}%)")
    print(f"\n✅ Refactorización completada exitosamente")
    print(f"   Archivo modificado: {archivo}")
    print(f"   Backup guardado en: {backup}")
    
    return True

if __name__ == "__main__":
    try:
        refactorizar_pacientes()
    except Exception as e:
        print(f"❌ Error durante la refactorización: {e}")
        print("   El backup se mantiene intacto")
        raise
