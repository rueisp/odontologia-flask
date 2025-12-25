
import os
import uuid
from datetime import datetime, date
import cloudinary
import cloudinary.uploader
import pytz
from flask import request, jsonify, flash, current_app
from sqlalchemy import or_
from ..extensions import db
# IMPORTANTE: Asegúrate de importar EPS y Municipio aquí
from ..models import Paciente, Cita, Evolucion, AuditLog, EPS, Municipio
from ..utils import allowed_file, convertir_a_fecha, extract_public_id_from_url


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
    # Esto arregla el error de que la imagen se borre al editar
    if base64_string.startswith('http'): 
        return base64_string 

    if base64_string.startswith('data:image'):
        try:
            # Lógica de nombre: Si hay ID de paciente, ÚSALO. Si no, usa el específico o temporal.
            if patient_id and str(patient_id) != "new_patient":
                public_id = f"dentigrama_paciente_{patient_id}"
            else:
                public_id = specific_public_id or f"temp_dentigrama_{uuid.uuid4().hex}"

            # Limpiamos el nombre para evitar carpetas duplicadas si el ID ya trae la carpeta
            if "/" in public_id:
                public_id = public_id.split("/")[-1]

            upload_result = cloudinary.uploader.upload(
                base64_string,
                folder="dentigramas_pacientes",
                public_id=public_id,
                overwrite=True,      # ¡Clave! Sobreescribe si existe
                invalidate=True,     # Limpia la caché visual
                resource_type="image"
            )
            return upload_result.get('secure_url')
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
    imagenes = [paciente.imagen_perfil_url, paciente.imagen_1, paciente.imagen_2, paciente.dentigrama_canvas]
    for url in imagenes:
        delete_from_cloudinary(url)


# =========================================================================
# === SERVICIOS DE LÓGICA DE NEGOCIO ===
# =========================================================================

def listar_pacientes_service(usuario, page, search_term):
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
    
    return query.order_by(Paciente.id.desc()).paginate(page=page, per_page=7, error_out=False)


def obtener_paciente_service(paciente_id, usuario):
    # 1. Buscar Paciente
    query = Paciente.query.filter_by(id=paciente_id, is_deleted=False)
    if not usuario.is_admin:
        query = query.filter_by(odontologo_id=usuario.id)
    paciente = query.first_or_404()

    # =======================================================
    # ▼▼▼ LÓGICA DE ENRIQUECIMIENTO (BÚSQUEDA INTELIGENTE) ▼▼▼
    # =======================================================
    
    # --- A. Búsqueda de Aseguradora (EPS) ---
    nombre_eps_display = paciente.aseguradora or 'No especificado'
    
    if paciente.codigo_aseguradora:
        # Limpiamos espacios y buscamos ignorando mayúsculas/minúsculas (ilike)
        cod_eps = str(paciente.codigo_aseguradora).strip()
        eps_obj = EPS.query.filter(EPS.codigo.ilike(cod_eps)).first()
        
        if eps_obj:
            nombre_eps_display = eps_obj.nombre
        else:
            # Si no encuentra el nombre, mostramos el código para que sepas qué buscar
            nombre_eps_display = f"{cod_eps} (Nombre no encontrado)"

    # --- B. Búsqueda de Municipio y Departamento ---
    nombre_municipio_display = paciente.municipio or 'No especificado'
    nombre_departamento_display = paciente.departamento or 'No especificado'

    if paciente.codigo_municipio and paciente.codigo_departamento:
        cod_mpio = str(paciente.codigo_municipio).strip()
        cod_dpto = str(paciente.codigo_departamento).strip()

        # Intento 1: Búsqueda exacta (ej: busca '47189')
        mpio_obj = Municipio.query.filter_by(codigo=cod_mpio).first()
        
        # Intento 2: Si falló, intentar con código corto (últimos 3 dígitos)
        # Esto arregla el caso donde el paciente tiene '47189' pero la BD tiene '189'
        if not mpio_obj and len(cod_mpio) > 2:
            cod_corto = cod_mpio[-3:] 
            mpio_obj = Municipio.query.filter_by(codigo=cod_corto, codigo_departamento=cod_dpto).first()

        if mpio_obj:
            nombre_municipio_display = mpio_obj.nombre
            nombre_departamento_display = mpio_obj.nombre_departamento

    # =======================================================
    # ▼▼▼ DICCIONARIO FINAL ▼▼▼
    # =======================================================
    paciente_data = {
        'id': paciente.id,
        'nombres': paciente.nombres or 'N/A',
        'apellidos': paciente.apellidos or 'N/A',
        'primer_nombre': paciente.primer_nombre or '',
        'segundo_nombre': paciente.segundo_nombre or '',
        'primer_apellido': paciente.primer_apellido or '',
        'segundo_apellido': paciente.segundo_apellido or '',
        'tipo_documento': paciente.tipo_documento or '',
        'documento': paciente.documento or 'N/A',
        'telefono': paciente.telefono or 'N/A',
        'email': paciente.email or 'N/A',
        'fecha_nacimiento': paciente.fecha_nacimiento.strftime('%d/%m/%Y') if isinstance(paciente.fecha_nacimiento, (date, datetime)) else 'N/A',
        'edad': f"{paciente.edad} años" if paciente.edad is not None else 'N/A',
        'genero': paciente.genero or 'N/A',
        'estado_civil': paciente.estado_civil or 'N/A',
        'ocupacion': paciente.ocupacion or 'N/A',
        
        # --- Imágenes ---
        'dentigrama_canvas': paciente.dentigrama_canvas,
        'imagen_perfil_url': paciente.imagen_perfil_url,
        'imagen_1': paciente.imagen_1,
        'imagen_2': paciente.imagen_2,
        
        # --- Ubicación ---
        'direccion': paciente.direccion or 'N/A',
        'barrio': paciente.barrio or 'N/A',

        # --- CAMPOS ENRIQUECIDOS (Aquí usamos las variables calculadas) ---
        'municipio': nombre_municipio_display,       
        'departamento': nombre_departamento_display, 
        'aseguradora': nombre_eps_display,           
        # -----------------------------------------------------------------

        # --- CAMPOS TÉCNICOS RIPS (Códigos originales) ---
        'tipo_vinculacion': paciente.tipo_vinculacion or 'N/A',
        'codigo_aseguradora': paciente.codigo_aseguradora or 'No especificado',
        'tipo_usuario_rips': paciente.tipo_usuario_rips or 'No especificado',
        'tipo_afiliado': paciente.tipo_afiliado or 'No especificado',
        'zona_residencia': paciente.zona_residencia or 'U', 
        'codigo_departamento': paciente.codigo_departamento or 'No especificado',
        'codigo_municipio': paciente.codigo_municipio or 'No especificado',
        
        # --- Resto de campos ---
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

    evoluciones_procesadas = []
    if paciente.evoluciones:
        evoluciones_ordenadas = sorted(paciente.evoluciones, key=lambda evo: evo.fecha, reverse=True)
        for evolucion_obj in evoluciones_ordenadas:
            evoluciones_procesadas.append({
                'id': evolucion_obj.id,
                'descripcion': evolucion_obj.descripcion,
                'fecha_formateada': evolucion_obj.fecha.strftime('%d de %B, %Y') if isinstance(evolucion_obj.fecha, (date, datetime)) else 'N/A'
            })

    full_public_id_trazos = None
    if paciente.dentigrama_canvas:
        try:
            full_public_id_trazos = extract_public_id_from_url(paciente.dentigrama_canvas)
        except Exception as e:
            full_public_id_trazos = None

    return paciente_data, evoluciones_procesadas, full_public_id_trazos


def agregar_evolucion_service(paciente_id, descripcion, usuario):
    query = Paciente.query.filter_by(id=paciente_id, is_deleted=False)
    if not usuario.is_admin:
        query = query.filter_by(odontologo_id=usuario.id)
    paciente = query.first_or_404()

    if not descripcion or not descripcion.strip():
        return {'success': False, 'message': 'La descripción no puede estar vacía.'}

    local_tz = pytz.timezone('America/Bogota')
    fecha_local = datetime.now(local_tz).date()

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
        return {'success': False, 'message': 'Error al guardar evolución.'}

def crear_paciente_service(form_data, files, usuario):
    # 1. Validación básica
    documento = form_data.get('documento')
    if not documento:
        return {'success': False, 'message': 'El documento es obligatorio.'}

    # 2. Validación de duplicados
    if Paciente.query.filter_by(documento=documento, is_deleted=False).first():
        return {'success': False, 'message': f'El paciente con documento {documento} ya existe.'}
    
    try:
        # --- A. Procesar Aseguradora (EPS) ---
        cod_eps = form_data.get('codigo_aseguradora')
        nombre_eps_guardar = form_data.get('aseguradora')

        if cod_eps:
            eps_obj = EPS.query.filter_by(codigo=cod_eps).first()
            if eps_obj: nombre_eps_guardar = eps_obj.nombre
        
        # --- B. Procesar Municipio y Departamento ---
        cod_dpto = form_data.get('codigo_dpto')
        cod_mpio = form_data.get('codigo_mpio')
        nombre_mpio_guardar = form_data.get('municipio')
        nombre_dpto_guardar = form_data.get('departamento')

        if cod_mpio:
            mpio_obj = Municipio.query.filter_by(codigo=cod_mpio).first()
            if not mpio_obj and len(cod_mpio) > 3 and cod_dpto:
                short_code = cod_mpio[-3:]
                mpio_obj = Municipio.query.filter_by(codigo=short_code, codigo_departamento=cod_dpto).first()

            if mpio_obj:
                nombre_mpio_guardar = mpio_obj.nombre
                nombre_dpto_guardar = mpio_obj.nombre_departamento

        # ==============================================================================
        # PROCESAMIENTO DENTIGRAMA (FASE 1: Subida inicial / Temporal)
        # ==============================================================================
        primer_nombre = form_data.get('primer_nombre', '').strip()
        primer_apellido = form_data.get('primer_apellido', '').strip()

        raw_dentigrama = form_data.get('dentigrama_url') or form_data.get('dentigrama_canvas')
        
        # Corrección: Obtenemos el ID temporal que viene del input hidden del HTML
        public_id_temporal = form_data.get('dentigrama_public_id') 

        dentigrama_final_url = None
        
        if raw_dentigrama:
             # Pasamos el ID temporal explícitamente para que Cloudinary sepa cuál es
             dentigrama_final_url = upload_base64_dentigrama(
                 raw_dentigrama, 
                 "new_patient", 
                 specific_public_id=public_id_temporal 
             )

        nuevo_paciente = Paciente(
            # --- Datos Personales ---
            nombres=f"{primer_nombre} {form_data.get('segundo_nombre', '').strip()}".strip(),
            apellidos=f"{primer_apellido} {form_data.get('segundo_apellido', '').strip()}".strip(),
            primer_nombre=primer_nombre,
            segundo_nombre=form_data.get('segundo_nombre', '').strip(),
            primer_apellido=primer_apellido,
            segundo_apellido=form_data.get('segundo_apellido', '').strip(),
            tipo_documento=form_data.get('tipo_documento'),
            documento=documento,
            fecha_nacimiento=convertir_a_fecha(form_data.get('fecha_nacimiento')),
            edad=int(form_data.get('edad')) if form_data.get('edad') else None,
            email=form_data.get('email'),
            telefono=form_data.get('telefono'),
            genero=form_data.get('genero'),
            estado_civil=form_data.get('estado_civil'),
            
            # --- Ubicación ---
            direccion=form_data.get('direccion'),
            barrio=form_data.get('barrio'),
            ocupacion=form_data.get('ocupacion'),
            municipio=nombre_mpio_guardar,
            departamento=nombre_dpto_guardar,
            aseguradora=nombre_eps_guardar,
            
            # --- RIPS ---
            tipo_vinculacion=form_data.get('tipo_vinculacion'),
            codigo_aseguradora=cod_eps,
            codigo_departamento=cod_dpto,
            codigo_municipio=cod_mpio,
            tipo_usuario_rips=form_data.get('tipo_usuario_rips'),
            tipo_afiliado=form_data.get('tipo_afiliado'),
            zona_residencia=form_data.get('zona_residencia'),

            # --- Historia Clínica ---
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
            
            # --- Sistema ---
            dentigrama_canvas=dentigrama_final_url,
            odontologo_id=usuario.id
        )

        # 3. Subida de Imágenes Adicionales
        if 'imagen_perfil' in files:
            nuevo_paciente.imagen_perfil_url = upload_file_to_cloudinary(files['imagen_perfil'], "pacientes_perfil")
        if 'imagen_1' in files:
            nuevo_paciente.imagen_1 = upload_file_to_cloudinary(files['imagen_1'], "paciente_imagenes")
        if 'imagen_2' in files:
            nuevo_paciente.imagen_2 = upload_file_to_cloudinary(files['imagen_2'], "paciente_imagenes")

        # 4. GUARDAR INICIAL (Obtenemos el ID del paciente)
        db.session.add(nuevo_paciente)
        db.session.commit()

        # ==============================================================================
        # ▼▼▼ CORRECCIÓN DEFINITIVA RENOMBRADO (ANTI-DUPLICADOS) ▼▼▼
        # ==============================================================================
        # Usamos el public_id_temporal que vino del formulario. Es más seguro que extraerlo de la URL.
        # Si existe y contiene "temp_", lo renombramos al ID definitivo.
        if public_id_temporal and "temp_" in public_id_temporal:
            try:
                # Nombre final deseado: dentigramas_pacientes/dentigrama_paciente_{id}
                final_public_id = f"dentigramas_pacientes/dentigrama_paciente_{nuevo_paciente.id}"
                
                # Si el input venía solo como nombre (sin carpeta), le agregamos la carpeta para que Cloudinary lo encuentre
                current_public_id_full = public_id_temporal
                if "/" not in current_public_id_full:
                     current_public_id_full = f"dentigramas_pacientes/{public_id_temporal}"

                # Renombrar en Cloudinary (Mueve el archivo, overwrite=True borra si ya existía basura ahí)
                upload_response = cloudinary.uploader.rename(
                    current_public_id_full, 
                    final_public_id, 
                    overwrite=True
                )
                
                # Actualizar URL en BD con la nueva dirección renombrada
                nuevo_paciente.dentigrama_canvas = upload_response.get('secure_url')
                db.session.commit()
                
            except Exception as e:
                # Si falla (ej: no encontró la imagen), registramos el error pero no bloqueamos el flujo
                current_app.logger.warning(f"No se pudo renombrar dentigrama: {e}")

        # 5. Contador
        try:
            from clinica.services.plan_service import PlanService
            PlanService.incrementar_contador_paciente(usuario.id)
        except Exception:
            pass

        return {'success': True, 'message': 'Paciente guardado con éxito', 'paciente_id': nuevo_paciente.id}

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error FATAL al guardar paciente: {e}', exc_info=True)
        return {'success': False, 'message': 'Ocurrió un error inesperado al guardar el paciente.'}

def editar_paciente_service(paciente_id, form_data, files, usuario):
    # Buscar paciente asegurando permisos
    query = Paciente.query.filter_by(id=paciente_id, is_deleted=False)
    if not usuario.is_admin:
        query = query.filter_by(odontologo_id=usuario.id)
    paciente = query.first_or_404()
    
    try:
        # ==============================================================================
        # 1. DATOS BÁSICOS
        # ==============================================================================
        primer_nombre = form_data.get('primer_nombre', '').strip()
        primer_apellido = form_data.get('primer_apellido', '').strip()

        paciente.primer_nombre = primer_nombre
        paciente.segundo_nombre = form_data.get('segundo_nombre', '').strip()
        paciente.primer_apellido = primer_apellido
        paciente.segundo_apellido = form_data.get('segundo_apellido', '').strip()
        
        paciente.nombres = f"{paciente.primer_nombre} {paciente.segundo_nombre}".strip()
        paciente.apellidos = f"{paciente.primer_apellido} {paciente.segundo_apellido}".strip()
        
        paciente.tipo_documento = form_data.get('tipo_documento')
        paciente.documento = form_data.get('documento')
        paciente.email = form_data.get('email')
        paciente.fecha_nacimiento = convertir_a_fecha(form_data.get('fecha_nacimiento', ''))
        paciente.edad = form_data.get('edad', type=int)
        paciente.telefono = form_data.get('telefono')
        paciente.genero = form_data.get('genero')
        paciente.estado_civil = form_data.get('estado_civil')
        paciente.ocupacion = form_data.get('ocupacion')
        paciente.direccion = form_data.get('direccion')
        paciente.barrio = form_data.get('barrio')

        # ==============================================================================
        # 2. RIPS Y UBICACIÓN
        # ==============================================================================
        cod_eps = form_data.get('codigo_aseguradora', '').strip()
        cod_dpto = form_data.get('codigo_dpto', '').strip()
        cod_mpio = form_data.get('codigo_mpio', '').strip()

        paciente.codigo_aseguradora = cod_eps
        paciente.codigo_departamento = cod_dpto
        paciente.codigo_municipio = cod_mpio
        
        if cod_eps:
            eps_obj = EPS.query.filter(EPS.codigo.ilike(cod_eps)).first()
            paciente.aseguradora = eps_obj.nombre if eps_obj else form_data.get('aseguradora')
        else:
            paciente.aseguradora = form_data.get('aseguradora')

        municipio_encontrado = False
        if cod_mpio and cod_dpto:
            mpio_obj = Municipio.query.filter_by(codigo=cod_mpio).first()
            if not mpio_obj and len(cod_mpio) > 2:
                cod_corto = cod_mpio[-3:]
                mpio_obj = Municipio.query.filter_by(codigo=cod_corto, codigo_departamento=cod_dpto).first()
            
            if mpio_obj:
                paciente.municipio = mpio_obj.nombre
                paciente.departamento = mpio_obj.nombre_departamento
                municipio_encontrado = True
        
        if not municipio_encontrado:
            raw_municipio = form_data.get('municipio')
            raw_departamento = form_data.get('departamento')
            if raw_municipio and not raw_municipio.strip().isdigit(): paciente.municipio = raw_municipio
            if raw_departamento and not raw_departamento.strip().isdigit(): paciente.departamento = raw_departamento

        paciente.tipo_vinculacion = form_data.get('tipo_vinculacion')
        paciente.tipo_usuario_rips = form_data.get('tipo_usuario_rips')
        paciente.tipo_afiliado = form_data.get('tipo_afiliado')
        paciente.zona_residencia = form_data.get('zona_residencia')
        
        # ==============================================================================
        # 3. DATOS CLÍNICOS
        # ==============================================================================
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

        # ==============================================================================
        # 4. GESTIÓN DE IMÁGENES
        # ==============================================================================
        if form_data.get('eliminar_imagen_perfil') == 'true':
            delete_from_cloudinary(paciente.imagen_perfil_url)
            paciente.imagen_perfil_url = None
        if form_data.get('eliminar_imagen_1') == 'true':
            delete_from_cloudinary(paciente.imagen_1)
            paciente.imagen_1 = None
        if form_data.get('eliminar_imagen_2') == 'true':
            delete_from_cloudinary(paciente.imagen_2)
            paciente.imagen_2 = None

        if 'imagen_perfil' in files and files['imagen_perfil'].filename != '':
             nueva_url = upload_file_to_cloudinary(files['imagen_perfil'], "pacientes_perfil")
             if nueva_url:
                 if paciente.imagen_perfil_url: delete_from_cloudinary(paciente.imagen_perfil_url)
                 paciente.imagen_perfil_url = nueva_url

        if 'imagen_1' in files and files['imagen_1'].filename != '':
             nueva_url = upload_file_to_cloudinary(files['imagen_1'], "paciente_imagenes")
             if nueva_url:
                 if paciente.imagen_1: delete_from_cloudinary(paciente.imagen_1)
                 paciente.imagen_1 = nueva_url

        if 'imagen_2' in files and files['imagen_2'].filename != '':
             nueva_url = upload_file_to_cloudinary(files['imagen_2'], "paciente_imagenes")
             if nueva_url:
                 if paciente.imagen_2: delete_from_cloudinary(paciente.imagen_2)
                 paciente.imagen_2 = nueva_url

        # ==============================================================================
        # 5. GESTIÓN DEL DENTIGRAMA (CORREGIDO - ERROR DE BORRADO)
        # ==============================================================================
        raw_dentigrama = form_data.get('dentigrama_url') or form_data.get('dentigrama_canvas')
        
        if raw_dentigrama:
            # 1. Subimos (o validamos) la imagen. Como usamos el ID del paciente, 
            # Cloudinary SOBREESCRIBE el archivo existente.
            nueva_url = upload_base64_dentigrama(raw_dentigrama, paciente.id)
            
            if nueva_url:
                # ⚠️ IMPORTANTE: ELIMINAMOS EL DELETE AQUÍ ⚠️
                # No debemos borrar 'paciente.dentigrama_canvas' antiguo, porque al tener
                # el mismo nombre público que el nuevo, borraríamos lo que acabamos de subir.
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


def subir_dentigrama_service(image_data, patient_id):
    """Sube un dentigrama a Cloudinary (Usa Helper Seguro)."""
    if not image_data:
        return {'success': False, 'message': 'No se proporcionaron datos de imagen'}

    try:
        url = upload_base64_dentigrama(image_data, patient_id)
        
        if url:
            # Actualizar BD inmediatamente si hay paciente
            if patient_id:
                patient = Paciente.query.get(patient_id)
                if patient:
                     if patient.dentigrama_canvas and patient.dentigrama_canvas != url:
                        delete_from_cloudinary(patient.dentigrama_canvas)
                     patient.dentigrama_canvas = url
                     db.session.commit()
            
            return {'success': True, 'url': url, 'message': 'Dentigrama subido exitosamente'}
        else:
            return {'success': False, 'message': 'Error al subir el dentigrama a Cloudinary.'}

    except Exception as e:
        return {'success': False, 'message': 'Ocurrió un error inesperado al subir el dentigrama.'}