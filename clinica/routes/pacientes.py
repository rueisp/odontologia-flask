import os
import base64
from uuid import uuid4
from datetime import date, datetime
import cloudinary
import cloudinary.uploader
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_, func, case
from ..extensions import db
from ..models import Paciente, Cita, Evolucion, AuditLog
from ..utils import allowed_file, convertir_a_fecha, extract_public_id_from_url # Asegúrate de que extract_public_id_from_url esté correctamente definida en tu utils.py
import io
import uuid 
import pytz # <--- ¡IMPORTAR pytz!

# =========================================================================
# === FUNCIONES AUXILIARES (MOVIDAS AL PRINCIPIO DEL ARCHIVO) ===
# =========================================================================

# Función auxiliar para convertir string a fecha 
def convertir_a_fecha(fecha_str):
    if fecha_str:
        from datetime import datetime
        try:
            return datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    return None

# Función auxiliar para subir archivos a Cloudinary (más genérica)
def upload_file_to_cloudinary(file, folder_name="general_uploads"):
    """Sube un objeto FileStorage a Cloudinary y devuelve su URL segura.
    Retorna la URL segura si tiene éxito, None en caso contrario.
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

# Función auxiliar para borrar archivos de Cloudinary
def delete_from_cloudinary(url):
    """Borra un recurso de Cloudinary dada su URL."""
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

# =========================================================================
# === FIN FUNCIONES AUXILIARES ===
# =========================================================================




pacientes_bp = Blueprint('pacientes', __name__, url_prefix='/pacientes')



@pacientes_bp.route('/')
@login_required
def lista_pacientes():
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('buscar', '').strip()

    query = Paciente.query.filter(Paciente.is_deleted == False)

    if not current_user.is_admin:
        query = query.filter(Paciente.odontologo_id == current_user.id)

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
    
    print(f"Usuario: {current_user.username}, es admin: {current_user.is_admin}")
    print(f"Pacientes encontrados para este usuario: {pacientes.total}")

    return render_template('pacientes.html', pacientes=pacientes, buscar=search_term)



@pacientes_bp.route('/<int:id>', methods=['GET', 'POST'])
@login_required
def mostrar_paciente(id):
    query = Paciente.query.filter_by(id=id, is_deleted=False)
    if not current_user.is_admin:
        query = query.filter_by(odontologo_id=current_user.id)
    paciente = query.first_or_404()

    if request.method == 'POST':
        descripcion = request.form.get('descripcion')
        if descripcion and descripcion.strip():
            # --- MODIFICACIONES CLAVE PARA LA ZONA HORARIA EN EL POST ---
            local_timezone = pytz.timezone('America/Bogota') # <--- TU ZONA HORARIA
            now_in_local_tz = datetime.now(local_timezone)
            fecha_local_para_evolucion = now_in_local_tz.date() # Obtener solo la fecha
            # --- FIN MODIFICACIONES ---

            nueva_evolucion = Evolucion(
                descripcion=descripcion.strip(),
                paciente_id=paciente.id,
                fecha=fecha_local_para_evolucion # <--- ¡ASIGNAR LA FECHA LOCALIZADA!
            )
            db.session.add(nueva_evolucion)
            try:
                db.session.commit()
                flash('Evolución añadida correctamente.', 'success')
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error al añadir evolución para paciente {paciente.id}: {e}", exc_info=True)
                flash('Ocurrió un error al guardar la evolución.', 'danger')
        else:
            flash('La descripción de la evolución no puede estar vacía.', 'warning')
        return redirect(url_for('pacientes.mostrar_paciente', id=paciente.id))

    # --- Lógica de PREPARACIÓN DE DATOS en Python para la plantilla (¡CRÍTICO!) ---
    paciente_data_para_template = {
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

    # 2. Preparar las evoluciones para la plantilla (ya ordenadas y con fechas formateadas)
    evoluciones_procesadas = []
    if paciente.evoluciones:
        # Asegúrate de que la ordenación sea consistente.
        # sorted(..., key=lambda evo: evo.fecha) es bueno si 'fecha' es un objeto date/datetime.
        evoluciones_ordenadas_py = sorted(paciente.evoluciones, key=lambda evo: evo.fecha, reverse=True)
        for evolucion_obj in evoluciones_ordenadas_py:
            evoluciones_procesadas.append({
                'id': evolucion_obj.id,
                'descripcion': evolucion_obj.descripcion,
                # Formatear la fecha de evolución aquí en Python a una cadena
                # Si la fecha se guarda correctamente como un objeto 'date', esto funcionará bien.
                'fecha_formateada': evolucion_obj.fecha.strftime('%d de %B, %Y') if isinstance(evolucion_obj.fecha, (date, datetime)) else 'N/A'
            })

    # 3. Extraer el Public ID del dentigrama (se mantiene igual)
    full_public_id_trazos = None
    if paciente.dentigrama_canvas:
        try:
            full_public_id_trazos = extract_public_id_from_url(paciente.dentigrama_canvas)
        except Exception as e:
            print(f"DENTIGRAMA ERROR (Backend): Error al extraer public ID de dentigrama_canvas: {e}")
            full_public_id_trazos = None

    return render_template('mostrar_paciente.html',
                            paciente=paciente_data_para_template,
                            evoluciones_ordenadas=evoluciones_procesadas,
                            full_public_id_trazos=full_public_id_trazos,
                            current_full_path=request.full_path)


# === FUNCION crear_paciente ===
@pacientes_bp.route('/crear', methods=['GET', 'POST'])
@login_required
def crear_paciente(): # El endpoint es 'pacientes.crear_paciente'
    if request.method == 'POST':
        # *** MODIFICACIÓN CLAVE AQUÍ: Detección más fiable de AJAX ***
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' 
        # **************************************************************

        documento = request.form.get('documento')
        if not documento:
            if is_ajax:
                return jsonify({'success': False, 'error': 'El número de documento es obligatorio.'}), 400
            flash('El número de documento es obligatorio.', 'danger')
            paciente_temporal = Paciente()
            # ... (código para rellenar paciente_temporal en caso de error) ...
            return render_template('registrar_paciente.html', paciente=paciente_temporal)

        paciente_existente = Paciente.query.filter_by(documento=documento, is_deleted=False).first()
        if paciente_existente:
            if is_ajax:
                return jsonify({'success': False, 'error': f'Ya existe un paciente registrado con el documento {documento}.'}), 409 # Conflict
            flash(f'Ya existe un paciente registrado con el documento {documento}.', 'danger')
            paciente_temporal = Paciente()
            # ... (código para rellenar paciente_temporal en caso de error) ...
            return render_template('registrar_paciente.html', paciente=paciente_temporal)
        
        try:
            # ... (todos tus request.form.get() para obtener los datos) ...
            nombres = request.form.get('nombres')
            apellidos = request.form.get('apellidos')
            tipo_documento = request.form.get('tipo_documento')
            fecha_nacimiento = convertir_a_fecha(request.form.get('fecha_nacimiento'))
            edad = int(request.form.get('edad')) if request.form.get('edad') else None
            email = request.form.get('email')
            telefono = request.form.get('telefono')
            genero = request.form.get('genero')
            estado_civil = request.form.get('estado_civil')
            direccion = request.form.get('direccion')
            barrio = request.form.get('barrio')
            municipio = request.form.get('municipio')
            departamento = request.form.get('departamento')
            aseguradora = request.form.get('aseguradora')
            tipo_vinculacion = request.form.get('tipo_vinculacion')
            ocupacion = request.form.get('ocupacion')
            referido_por = request.form.get('referido_por')
            nombre_responsable = request.form.get('nombre_responsable')
            telefono_responsable = request.form.get('telefono_responsable')
            parentesco = request.form.get('parentesco')
            motivo_consulta = request.form.get('motivo_consulta')
            enfermedad_actual = request.form.get('enfermedad_actual')
            antecedentes_personales = request.form.get('antecedentes_personales')
            antecedentes_familiares = request.form.get('antecedentes_familiares')
            antecedentes_quirurgicos = request.form.get('antecedentes_quirurgicos')
            antecedentes_hemorragicos = request.form.get('antecedentes_hemorragicos')
            farmacologicos = request.form.get('farmacologicos')
            reaccion_medicamentos = request.form.get('reaccion_medicamentos')
            alergias = request.form.get('alergias')
            habitos = request.form.get('habitos')
            cepillado = request.form.get('cepillado')
            examen_fisico = request.form.get('examen_fisico')
            ultima_visita_odontologo = request.form.get('ultima_visita_odontologo', '')
            plan_tratamiento = request.form.get('plan_tratamiento')
            observaciones = request.form.get('observaciones', '')

            dentigrama_canvas = request.form.get('dentigrama_canvas') or None
            
            imagen_perfil_url = None
            if 'imagen_perfil' in request.files:
                file_perfil = request.files['imagen_perfil']
                # Check for file existence and allowed type before uploading
                if file_perfil and file_perfil.filename != '':
                    if not allowed_file(file_perfil.filename):
                        error_msg = 'Tipo de archivo no permitido para la imagen de perfil. Solo se permiten imágenes.'
                        current_app.logger.warning(f"CREAR_PACIENTE_ERROR: {error_msg} - filename: {file_perfil.filename}")
                        if is_ajax:
                            return jsonify({'success': False, 'error': error_msg}), 400
                        flash(error_msg, 'warning')
                    else:
                        imagen_perfil_url = upload_file_to_cloudinary(file_perfil, folder_name="pacientes_perfil")
                        if not imagen_perfil_url: # This means upload_file_to_cloudinary failed (Cloudinary error or other issue)
                            error_msg = 'Error al subir la imagen de perfil a Cloudinary. Por favor, revisa la configuración de Cloudinary y el archivo.'
                            current_app.logger.error(f"CREAR_PACIENTE_ERROR: {error_msg} para '{file_perfil.filename}'.")
                            if is_ajax:
                                return jsonify({'success': False, 'error': error_msg}), 500
                            flash(error_msg, 'warning')
                # If file_perfil is empty or filename is empty, imagen_perfil_url remains None, which is fine.


            imagen_1 = None
            if 'imagen_1' in request.files:
                file_imagen_1 = request.files['imagen_1']
                if file_imagen_1 and file_imagen_1.filename != '':
                    if not allowed_file(file_imagen_1.filename):
                        error_msg = 'Tipo de archivo no permitido para la Imagen 1. Solo se permiten imágenes.'
                        current_app.logger.warning(f"CREAR_PACIENTE_ERROR: {error_msg} - filename: {file_imagen_1.filename}")
                        if is_ajax:
                            return jsonify({'success': False, 'error': error_msg}), 400
                        flash(error_msg, 'warning')
                    else:
                        imagen_1 = upload_file_to_cloudinary(file_imagen_1, folder_name="paciente_imagenes")
                        if not imagen_1:
                            error_msg = 'Error al subir la Imagen 1 a Cloudinary. Por favor, revisa la configuración de Cloudinary y el archivo.'
                            current_app.logger.error(f"CREAR_PACIENTE_ERROR: {error_msg} para '{file_imagen_1.filename}'.")
                            if is_ajax:
                                return jsonify({'success': False, 'error': error_msg}), 500
                            flash(error_msg, 'warning')

            imagen_2 = None
            if 'imagen_2' in request.files:
                file_imagen_2 = request.files['imagen_2']
                if file_imagen_2 and file_imagen_2.filename != '':
                    if not allowed_file(file_imagen_2.filename):
                        error_msg = 'Tipo de archivo no permitido para la Imagen 2. Solo se permiten imágenes.'
                        current_app.logger.warning(f"CREAR_PACIENTE_ERROR: {error_msg} - filename: {file_imagen_2.filename}")
                        if is_ajax:
                            return jsonify({'success': False, 'error': error_msg}), 400
                        flash(error_msg, 'warning')
                    else:
                        imagen_2 = upload_file_to_cloudinary(file_imagen_2, folder_name="paciente_imagenes")
                        if not imagen_2:
                            error_msg = 'Error al subir la Imagen 2 a Cloudinary. Por favor, revisa la configuración de Cloudinary y el archivo.'
                            current_app.logger.error(f"CREAR_PACIENTE_ERROR: {error_msg} para '{file_imagen_2.filename}'.")
                            if is_ajax:
                                return jsonify({'success': False, 'error': error_msg}), 500
                            flash(error_msg, 'warning')


            nuevo_paciente = Paciente(
                nombres=nombres, apellidos=apellidos, tipo_documento=tipo_documento, documento=documento,
                fecha_nacimiento=fecha_nacimiento,
                telefono=telefono, edad=edad, email=email, genero=genero, estado_civil=estado_civil,
                direccion=direccion, barrio=barrio, municipio=municipio, departamento=departamento,
                aseguradora=aseguradora, tipo_vinculacion=tipo_vinculacion, ocupacion=ocupacion,
                referido_por=referido_por, nombre_responsable=nombre_responsable,
                telefono_responsable=telefono_responsable, parentesco=parentesco,
                motivo_consulta=motivo_consulta, enfermedad_actual=enfermedad_actual,
                antecedentes_personales=antecedentes_personales, antecedentes_familiares=antecedentes_familiares,
                antecedentes_quirurgicos=antecedentes_quirurgicos, antecedentes_hemorragicos=antecedentes_hemorragicos,
                farmacologicos=farmacologicos, reaccion_medicamentos=reaccion_medicamentos,
                alergias=alergias, habitos=habitos, cepillado=cepillado, examen_fisico=examen_fisico,
                ultima_visita_odontologo=ultima_visita_odontologo, plan_tratamiento=plan_tratamiento,
                observaciones=observaciones, dentigrama_canvas=dentigrama_canvas,
                imagen_perfil_url=imagen_perfil_url,
                imagen_1=imagen_1, imagen_2=imagen_2, 
                odontologo_id=current_user.id
            )

            db.session.add(nuevo_paciente)
            db.session.commit()

            # --- ESTE BLOQUE YA ESTABA BIEN PARA LA RESPUESTA AJAX ---
            if is_ajax:
                return jsonify({
                    'success': True,
                    'message': 'Paciente guardado exitosamente.',
                    'redirect_url': url_for('pacientes.lista_pacientes')
                }), 200
            # *********************************************************
            
            flash('Paciente guardado con éxito', 'success')
            return redirect(url_for('pacientes.lista_pacientes'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error FATAL al guardar paciente: {e}', exc_info=True)
            
            # --- ESTE BLOQUE YA ESTABA BIEN PARA LA RESPUESTA AJAX ---
            if is_ajax:
                return jsonify({
                    'success': False,
                    'error': 'Ocurrió un error inesperado al guardar el paciente. Por favor, revisa los datos.',
                    'details': str(e) # This 'details' will now show exceptions that happen *after* file upload attempts.
                }), 500 
            # *********************************************************
            
            flash('Ocurrió un error inesperado al guardar el paciente. Por favor, revisa los datos.', 'danger')
            paciente_con_error = Paciente()
            # ... (código para rellenar paciente_con_error en caso de error) ...
            return render_template('registrar_paciente.html', paciente=paciente_con_error)

    # Para GET requests
    paciente_vacio = Paciente()
    paciente_vacio.fecha_nacimiento = '' 
    return render_template('registrar_paciente.html', paciente=paciente_vacio)

@pacientes_bp.route('/<int:id>/borrar', methods=['POST'])
@login_required
def borrar_paciente(id):
    
    query = Paciente.query.filter_by(id=id)

    if not current_user.is_admin:
        query = query.filter_by(odontologo_id=current_user.id)
        
    # 3. Obtener el paciente o devolver 404 (nuestro guardián de seguridad)
    paciente = query.first_or_404()
    
    # --- El resto de tu lógica de soft-delete está bien ---
    if paciente.is_deleted:
        flash(f"El paciente '{paciente.nombres} {paciente.apellidos}' ya se encuentra en la papelera.", 'info')
        return redirect(url_for('pacientes.lista_pacientes'))

    paciente_nombre_completo_para_log = f"{paciente.nombres} {paciente.apellidos}"
    
    try:
        # --- NUEVA LÓGICA: Eliminar imágenes asociadas de Cloudinary ---
        current_app.logger.info(f"PACIENTE_BORRADO: Iniciando eliminación de imágenes de Cloudinary para paciente ID {paciente.id}")

        # Imagen de Perfil
        if paciente.imagen_perfil_url:
            if delete_from_cloudinary(paciente.imagen_perfil_url):
                paciente.imagen_perfil_url = None # Opcional: limpiar la URL en BD si se borra de Cloudinary
                current_app.logger.debug(f"PACIENTE_BORRADO: Imagen de perfil eliminada de Cloudinary para paciente ID {paciente.id}")
            else:
                current_app.logger.warning(f"PACIENTE_BORRADO: Falló la eliminación de imagen de perfil de Cloudinary para paciente ID {paciente.id}")

        # Imagen 1
        if paciente.imagen_1:
            if delete_from_cloudinary(paciente.imagen_1):
                paciente.imagen_1 = None
                current_app.logger.debug(f"PACIENTE_BORRADO: Imagen 1 eliminada de Cloudinary para paciente ID {paciente.id}")
            else:
                current_app.logger.warning(f"PACIENTE_BORRADO: Falló la eliminación de Imagen 1 de Cloudinary para paciente ID {paciente.id}")

        # Imagen 2
        if paciente.imagen_2:
            if delete_from_cloudinary(paciente.imagen_2):
                paciente.imagen_2 = None
                current_app.logger.debug(f"PACIENTE_BORRADO: Imagen 2 eliminada de Cloudinary para paciente ID {paciente.id}")
            else:
                current_app.logger.warning(f"PACIENTE_BORRADO: Falló la eliminación de Imagen 2 de Cloudinary para paciente ID {paciente.id}")
        
        # Dentigrama
        if paciente.dentigrama_canvas:
            if delete_from_cloudinary(paciente.dentigrama_canvas):
                paciente.dentigrama_canvas = None
                current_app.logger.debug(f"PACIENTE_BORRADO: Dentigrama eliminado de Cloudinary para paciente ID {paciente.id}")
            else:
                current_app.logger.warning(f"PACIENTE_BORRADO: Falló la eliminación del Dentigrama de Cloudinary para paciente ID {paciente.id}")
        
        current_app.logger.info(f"PACIENTE_BORRADO: Finalizada la eliminación de imágenes de Cloudinary para paciente ID {paciente.id}")
        # --- FIN NUEVA LÓGICA ---

        # --- Lógica de soft-delete existente ---
        paciente.is_deleted = True
        paciente.deleted_at = datetime.utcnow()

        # Soft delete en cascada para las citas
        citas_del_paciente = Cita.query.filter_by(paciente_id=paciente.id, is_deleted=False).all()
        for cita_item in citas_del_paciente:
            cita_item.is_deleted = True
            cita_item.deleted_at = datetime.utcnow()

        # Crear el log de auditoría
        log_descripcion = f"Paciente '{paciente_nombre_completo_para_log}' movido a la papelera."
        if citas_del_paciente:
            log_descripcion += f" También se movieron {len(citas_del_paciente)} cita(s) asociadas."
            
        audit_entry = AuditLog(
            action_type="SOFT_DELETE_PACIENTE",
            description=log_descripcion,
            target_model="Paciente",
            target_id=paciente.id,
            user_id=current_user.id,
            user_username=current_user.username
        )
        db.session.add(audit_entry)
        
        db.session.commit() 
        
        flash(f"Paciente '{paciente_nombre_completo_para_log}' movido a la papelera.", 'success')

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al mover paciente ID {id} a la papelera: {str(e)}", exc_info=True)
        flash('Ocurrió un error al mover el paciente a la papelera.', 'danger')
        
    return redirect(url_for('pacientes.lista_pacientes'))



# clinica/routes/pacientes.py (función editar_paciente)

# ... (mantén tus importaciones existentes) ...

@pacientes_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_paciente(id):
    query = Paciente.query.filter_by(id=id, is_deleted=False)
    if not current_user.is_admin:
        query = query.filter_by(odontologo_id=current_user.id)
    paciente = query.first_or_404()
    
    if request.method == 'POST':
        current_app.logger.debug(f"DEBUG - editar_paciente POST: Iniciando para paciente ID {id}.")
        try:
            current_app.logger.debug("DEBUG - editar_paciente POST: Entrando al bloque try.")
            # --- 1. ACTUALIZACIÓN DE DATOS DE TEXTO ---
            paciente.nombres = request.form.get('nombres')
            paciente.apellidos = request.form.get('apellidos')
            paciente.tipo_documento = request.form.get('tipo_documento')
            paciente.documento = request.form.get('documento')
            paciente.email = request.form.get('email')
            current_app.logger.debug("DEBUG - editar_paciente POST: Datos de texto actualizados.")

            paciente.fecha_nacimiento = convertir_a_fecha(request.form.get('fecha_nacimiento', ''))
            paciente.edad = request.form.get('edad', type=int) 
            paciente.telefono = request.form.get('telefono') 
            
            paciente.genero = request.form.get('genero')
            paciente.estado_civil = request.form.get('estado_civil')
            paciente.direccion = request.form.get('direccion')
            paciente.barrio = request.form.get('barrio')
            paciente.municipio = request.form.get('municipio')
            paciente.departamento = request.form.get('departamento')
            paciente.aseguradora = request.form.get('aseguradora')
            paciente.tipo_vinculacion = request.form.get('tipo_vinculacion')
            paciente.ocupacion = request.form.get('ocupacion')
            paciente.referido_por = request.form.get('referido_por')
            paciente.nombre_responsable = request.form.get('nombre_responsable')
            paciente.telefono_responsable = request.form.get('telefono_responsable')
            paciente.parentesco = request.form.get('parentesco')
            paciente.motivo_consulta = request.form.get('motivo_consulta')
            paciente.enfermedad_actual = request.form.get('enfermedad_actual')
            paciente.antecedentes_personales = request.form.get('antecedentes_personales')
            paciente.antecedentes_familiares = request.form.get('antecedentes_familiares')
            paciente.antecedentes_quirurgicos = request.form.get('antecedentes_quirurgicos') 
            paciente.antecedentes_hemorragicos = request.form.get('antecedentes_hemorragicos')
            paciente.farmacologicos = request.form.get('farmacologicos')
            paciente.reaccion_medicamentos = request.form.get('reaccion_medicamentos')
            paciente.alergias = request.form.get('alergias')
            paciente.habitos = request.form.get('habitos')
            paciente.cepillado = request.form.get('cepillado')
            paciente.examen_fisico = request.form.get('examen_fisico')
            paciente.ultima_visita_odontologo = request.form.get('ultima_visita_odontologo')
            paciente.plan_tratamiento = request.form.get('plan_tratamiento')
            paciente.observaciones = request.form.get('observaciones')
            current_app.logger.debug("DEBUG - editar_paciente POST: Campos adicionales actualizados.")

            # --- 2. MANEJO DE ELIMINACIÓN DE IMÁGENES (checkboxes) ---
            
            # --- Eliminar Imagen de Perfil ---
            if 'eliminar_imagen_perfil' in request.form and paciente.imagen_perfil_url:
                delete_from_cloudinary(paciente.imagen_perfil_url)
                paciente.imagen_perfil_url = None
                current_app.logger.debug("DEBUG - editar_paciente POST: Imagen de perfil eliminada.")

            # Eliminar imagen_1
            if 'eliminar_imagen_1' in request.form and paciente.imagen_1: 
                delete_from_cloudinary(paciente.imagen_1)
                paciente.imagen_1 = None
                current_app.logger.debug("DEBUG - editar_paciente POST: Imagen 1 eliminada.")
            
            # Eliminar imagen_2
            if 'eliminar_imagen_2' in request.form and paciente.imagen_2: 
                delete_from_cloudinary(paciente.imagen_2)
                paciente.imagen_2 = None
                current_app.logger.debug("DEBUG - editar_paciente POST: Imagen 2 eliminada.")
            
            current_app.logger.debug("DEBUG - editar_paciente POST: Eliminación de imágenes completada.")

            # --- 3. MANEJO DE SUBIDA (REEMPLAZO) DE NUEVAS IMÁGENES ---
            
            # --- Subida/Reemplazo de Imagen de Perfil ---
            if 'imagen_perfil' in request.files:
                file_perfil = request.files['imagen_perfil']
                if file_perfil and file_perfil.filename != '':
                    if paciente.imagen_perfil_url: # Si ya existía una imagen, bórrala primero de Cloudinary
                        delete_from_cloudinary(paciente.imagen_perfil_url)
                    
                    nueva_imagen_perfil_url = upload_file_to_cloudinary(file_perfil, folder_name="pacientes_perfil")
                    if nueva_imagen_perfil_url:
                        paciente.imagen_perfil_url = nueva_imagen_perfil_url
                        current_app.logger.debug(f"DEBUG - CLOUDINARY: Nueva imagen de perfil subida: {paciente.imagen_perfil_url}")
                    else:
                        flash('Error al subir la nueva imagen de perfil. Revisa el archivo y la configuración de Cloudinary.', 'warning')
            
            current_app.logger.debug("DEBUG - editar_paciente POST: Procesando subida de nuevas imágenes.")
            # Para imagen_1
            if 'imagen_1' in request.files: 
                imagen_1_file = request.files['imagen_1']
                if imagen_1_file and imagen_1_file.filename != '':
                    if paciente.imagen_1: # Si ya existía una imagen, bórrala primero
                        delete_from_cloudinary(paciente.imagen_1)
                    
                    upload_result = upload_file_to_cloudinary(imagen_1_file, folder_name="paciente_imagenes")
                    if upload_result:
                        paciente.imagen_1 = upload_result # Asignar a campo de modelo
                        current_app.logger.debug(f"DEBUG - CLOUDINARY: Nueva imagen_1 subida: {paciente.imagen_1}")
                    else:
                        flash('Error al subir la nueva Imagen 1. Revisa el archivo y la configuración de Cloudinary.', 'warning')


            # Para imagen_2
            if 'imagen_2' in request.files: 
                imagen_2_file = request.files['imagen_2']
                if imagen_2_file and imagen_2_file.filename != '':
                    if paciente.imagen_2: # Si ya existía una imagen, bórrala primero
                        delete_from_cloudinary(paciente.imagen_2)
                    upload_result = upload_file_to_cloudinary(imagen_2_file, folder_name="paciente_imagenes")
                    if upload_result:
                        paciente.imagen_2 = upload_result # Asignar a campo de modelo
                        current_app.logger.debug(f"DEBUG - CLOUDINARY: Nueva imagen_2 subida: {paciente.imagen_2}")
                    else:
                        flash('Error al subir la nueva Imagen 2. Revisa el archivo y la configuración de Cloudinary.', 'warning')
            
            current_app.logger.debug("DEBUG - editar_paciente POST: Subida de nuevas imágenes completada.")

            # --- 4. MANEJO DEL DENTIGRAMA (ACTUALIZACIÓN/REEMPLAZO/ELIMINACIÓN) ---
            current_app.logger.debug("DEBUG - editar_paciente POST: Procesando dentigrama.")
            dentigrama_canvas_from_form = request.form.get('dentigrama_canvas') 

            current_app.logger.debug(f"DEBUG DENTIGRAMA: paciente.dentigrama_canvas (DB - ANTES DE GUARDAR): {paciente.dentigrama_canvas}")
            current_app.logger.debug(f"DEBUG DENTIGRAMA: dentigrama_canvas_from_form (FORM): {dentigrama_canvas_from_form}")

            if dentigrama_canvas_from_form: # Si el formulario envió una URL (nueva o la misma del JS)
                # SOLO BORRAR LA ANTIGUA SI LA NUEVA URL ES REALMENTE DIFERENTE
                if paciente.dentigrama_canvas and paciente.dentigrama_canvas != dentigrama_canvas_from_form:
                    public_id_antiguo = extract_public_id_from_url(paciente.dentigrama_canvas)
                    current_app.logger.debug(f"DEBUG DENTIGRAMA: Public ID Antiguo Extraído: {public_id_antiguo}") 
                    if public_id_antiguo:
                        current_app.logger.debug(f"DEBUG - CLOUDINARY: Eliminando antiguo dentigrama: {public_id_antiguo}")
                        delete_from_cloudinary(paciente.dentigrama_canvas) # <-- ¡DESCOMENTADA!
                paciente.dentigrama_canvas = dentigrama_canvas_from_form
                current_app.logger.debug(f"DEBUG - CLOUDINARY: Dentigrama URL actualizada a: {paciente.dentigrama_canvas}")
            elif not dentigrama_canvas_from_form and paciente.dentigrama_canvas: 
                # Si el formulario envió una URL vacía (el usuario limpió el dentigrama desde JS)
                # y el paciente tenía una URL previa, entonces borramos la antigua de Cloudinary
                public_id_antiguo = extract_public_id_from_url(paciente.dentigrama_canvas)
                current_app.logger.debug(f"DEBUG DENTIGRAMA: Public ID Antiguo Extraído (por limpieza): {public_id_antiguo}") 
                if public_id_antiguo:
                    current_app.logger.debug(f"DEBUG - CLOUDINARY: Eliminando dentigrama por limpieza: {public_id_antiguo}")
                    delete_from_cloudinary(paciente.dentigrama_canvas) # <-- ¡DESCOMENTADA!
                paciente.dentigrama_canvas = None 
                current_app.logger.debug("DEBUG - CLOUDINARY: Dentigrama URL establecida a None (limpiado).")
            current_app.logger.debug("DEBUG - editar_paciente POST: Procesamiento de dentigrama completado.")
            current_app.logger.debug("DEBUG - editar_paciente POST: Realizando commit a la base de datos.")
            db.session.commit()
            flash('Paciente actualizado correctamente', 'success')
            current_app.logger.info(f"PACIENTE: Paciente ID {paciente.id} actualizado con éxito.")
            current_app.logger.debug("DEBUG - editar_paciente POST: Retornando jsonify de éxito.")
            return jsonify({'message': 'Paciente actualizado correctamente', 'redirect_url': url_for('pacientes.mostrar_paciente', id=paciente.id)}), 200

        except Exception as e:
            current_app.logger.error("DEBUG - editar_paciente POST: ¡Excepción capturada en el bloque try/except!")
            db.session.rollback()
            current_app.logger.error(f'Error al editar paciente {id}: {e}', exc_info=True)
            if isinstance(paciente.fecha_nacimiento, (date, datetime)):
                paciente.fecha_nacimiento = paciente.fecha_nacimiento.strftime('%Y-%m-%d')
            else:
                paciente.fecha_nacimiento = request.form.get('fecha_nacimiento', '') 
            current_app.logger.debug("DEBUG - editar_paciente POST: Retornando jsonify de error.")
            return jsonify({'error': f'Error al actualizar el paciente: {str(e)}'}), 500

    current_app.logger.debug(f"DEBUG - editar_paciente GET: Renderizando plantilla para paciente ID {id}.")
    # --- LÓGICA PARA EL MÉTODO GET (¡CRÍTICO para formatear la fecha como string!) ---
    if isinstance(paciente.fecha_nacimiento, (date, datetime)):
        paciente.fecha_nacimiento = paciente.fecha_nacimiento.strftime('%Y-%m-%d')
    else:
        paciente.fecha_nacimiento = '' 

    return render_template('editar_paciente.html', paciente=paciente)





# Función para obtener el logger, para mayor consistencia
def get_logger():
    try:
        return current_app.logger
    except RuntimeError:
        # Fallback para entornos donde current_app no está disponible (ej. pruebas unitarias)
        import logging
        logging.basicConfig(level=logging.DEBUG)
        return logging.getLogger(__name__)

app_logger = get_logger()

# Importar db y Paciente desde tu módulo de la aplicación Flask
# Asegúrate de que estas líneas reflejen la estructura real de tu proyecto
try:
    from clinica import db
    from clinica.models import Paciente
except ImportError as e:
    app_logger.error(f"Error al importar db o Paciente: {e}. Asegúrate de que las rutas sean correctas.")
    db = None
    Paciente = None

# --- INICIO DE LA FUNCIÓN `upload_dentigrama` (CON CAMBIOS CRÍTICOS) ---
@pacientes_bp.route('/upload_dentigrama', methods=['POST'])
def upload_dentigrama():
    data = request.get_json()
    image_data = data.get('image_data')  # Datos Base64 de la imagen
    patient_id = data.get('patient_id')  # Puede ser None para un paciente nuevo o temporal

    if not image_data:
        current_app.logger.error("UPLOAD_DENTIGRAMA_ERROR: No se proporcionaron datos de imagen.")
        return jsonify({'error': 'No se proporcionaron datos de imagen'}), 400

    try:
        from clinica.models import Paciente # Se asegura de que el modelo esté disponible aquí

        patient = None
        old_dentigrama_url = None

        if patient_id:
            patient = Paciente.query.get(patient_id)
            if not patient:
                current_app.logger.warning(f"UPLOAD_DENTIGRAMA_WARNING: Paciente con ID {patient_id} no encontrado para actualizar dentigrama. La imagen se subirá pero no se vinculará a un paciente.")
                # Aquí podrías decidir si quieres retornar un error 404 o seguir como temporal.
                # Por ahora, seguimos para subir la imagen, pero no actualizamos la DB si el paciente no existe.
            else:
                # Si el paciente existe, guardamos la URL antigua para su posterior eliminación
                old_dentigrama_url = patient.dentigrama_canvas
                current_app.logger.debug(f"UPLOAD_DENTIGRAMA_DEBUG: Encontrada URL de dentigrama antigua para paciente {patient_id}: {old_dentigrama_url}")

        # Genera un nuevo public_id único para el nuevo dentigrama
        # Esto asegura que cada subida genere un recurso distinto en Cloudinary.
        # Luego borramos el anterior explícitamente.
        base_public_id = f"dentigrama_patient_{patient_id}" if patient_id else "dentigrama_temp_session"
        new_public_id = f"{base_public_id}_{uuid.uuid4().hex}" 

        current_app.logger.info(f"UPLOAD_DENTIGRAMA_INFO: Intentando subir nuevo dentigrama para paciente {patient_id if patient_id else 'temporal'} con public_id: {new_public_id}")

        upload_result = cloudinary.uploader.upload(
            image_data,
            folder="dentigramas",  # Tu carpeta en Cloudinary
            public_id=new_public_id
        )
        new_cloudinary_url = upload_result.get('secure_url')

        if not new_cloudinary_url:
            current_app.logger.error(f"UPLOAD_DENTIGRAMA_ERROR: Falló la subida a Cloudinary para paciente {patient_id if patient_id else 'temporal'}. Resultado: {upload_result}")
            return jsonify({'error': 'Error al subir el dentigrama a Cloudinary.'}), 500

        # Si la subida del nuevo dentigrama fue exitosa, gestiona la actualización de la BD y la eliminación del antiguo
        if patient:
            # Elimina el dentigrama anterior de Cloudinary si existía
            if old_dentigrama_url:
                if delete_from_cloudinary(old_dentigrama_url):
                    current_app.logger.info(f"UPLOAD_DENTIGRAMA_INFO: Dentigrama anterior {old_dentigrama_url} eliminado de Cloudinary para paciente {patient_id}.")
                else:
                    current_app.logger.warning(f"UPLOAD_DENTIGRAMA_WARNING: Falló la eliminación del dentigrama anterior {old_dentigrama_url} para paciente {patient_id}, pero se subió el nuevo.")

            # Actualiza el campo del paciente con la nueva URL
            patient.dentigrama_canvas = new_cloudinary_url
            db.session.commit()
            current_app.logger.info(f"UPLOAD_DENTIGRAMA_INFO: Dentigrama para paciente {patient_id} actualizado en BD. Nueva URL: {new_cloudinary_url}")
        else:
            current_app.logger.info(f"UPLOAD_DENTIGRAMA_INFO: Dentigrama temporal subido. URL: {new_cloudinary_url}. No asociado a paciente en BD por ahora.")

        return jsonify({'url': new_cloudinary_url, 'message': 'Dentigrama subido exitosamente'}), 200

    except Exception as e:
        db.session.rollback() # Asegura que se revierta la transacción si falla una operación de BD
        current_app.logger.error(f"UPLOAD_DENTIGRAMA_FATAL_ERROR: Error inesperado al subir dentigrama: {e}", exc_info=True)
        return jsonify({'error': 'Ocurrió un error inesperado al subir el dentigrama.', 'details': str(e)}), 500