
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
from ..utils import allowed_file, convertir_a_fecha, extract_public_id_from_url
from clinica.models import Paciente, Evolucion
pacientes_bp = Blueprint('pacientes', __name__, url_prefix='/pacientes')


@pacientes_bp.route('/')
@login_required
def lista_pacientes():
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('buscar', '').strip()

    # 1. Empieza con la consulta base (solo pacientes no borrados)
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



@pacientes_bp.route('/<int:id>', methods=['GET', 'POST']) # Cambiado a una URL más RESTful
@login_required # 1. Proteger la ruta, es fundamental
def mostrar_paciente(id):

    query = Paciente.query.filter_by(id=id, is_deleted=False)
    
    if not current_user.is_admin:
        query = query.filter_by(odontologo_id=current_user.id)
        
    paciente = query.first_or_404()
    
    if request.method == 'POST':
        # Corrección 1: Usar .get() con paréntesis, no con corchetes.
        descripcion = request.form.get('descripcion')
        
        if descripcion and descripcion.strip():
            nueva_evolucion = Evolucion(
                descripcion=descripcion.strip(),
                paciente_id=paciente.id # Usamos el id del paciente seguro que ya obtuvimos
                # La fecha se puede añadir por defecto en el modelo para más limpieza
            )
            db.session.add(nueva_evolucion)
            db.session.commit()
            flash('Evolución añadida correctamente.', 'success')
        else:
            flash('La descripción de la evolución no puede estar vacía.', 'warning')

        return redirect(url_for('pacientes.mostrar_paciente', id=paciente.id))

    # --- Lógica para el Dentigrama: Extraer el Public ID de los trazos ---
    full_public_id_trazos = None
    if paciente.dentigrama_url:
        try:
            # Obtener la parte del path de la URL después de "/upload/"
            # Ejemplo: "v1756665344/dentigramas_overlay/f197113usxh6merhww.png"
            parts = paciente.dentigrama_url.split('/upload/')
            if len(parts) > 1:
                # Obtener la parte que contiene la carpeta y el nombre del archivo
                public_id_with_version_and_ext = parts[1].strip('/') # Eliminar barras al inicio/fin
                
                # Dividir por '/' para obtener las partes
                path_components = public_id_with_version_and_ext.split('/')
                
                # Si la primera parte es una "versión" (ej. v1234567890), la ignoramos para el Public ID
                if path_components[0].startswith('v') and len(path_components) > 1:
                    actual_public_id_parts = path_components[1:]
                else:
                    actual_public_id_parts = path_components
                
                # Unir las partes restantes y quitar la extensión (ej. .png)
                full_public_id_trazos = '/'.join(actual_public_id_parts).split('.')[0]

        except Exception as e:
            print(f"DENTIGRAMA ERROR (Backend): Error al extraer public ID de dentigrama_url: {e}")
            full_public_id_trazos = None # Asegurar que sea None si hay un error
    # --- Fin Lógica para el Dentigrama ---

    return render_template('mostrar_paciente.html', 
                           paciente=paciente,
                           full_public_id_trazos=full_public_id_trazos) # <--- Pasamos la variable
@pacientes_bp.route('/crear', methods=['GET', 'POST'])
@login_required
def crear_paciente():
    if request.method == 'POST':
        documento = request.form.get('documento')
        if not documento:
            flash('El número de documento es obligatorio.', 'danger')
            # Creamos un paciente "falso" con los datos del form para repoblar
            paciente_temporal = Paciente(**request.form) 
            return render_template('registrar_paciente.html', form_data=request.form, paciente=paciente_temporal)

        paciente_existente = Paciente.query.filter_by(documento=documento).first()
        if paciente_existente:
            flash(f'Ya existe un paciente registrado con el documento {documento}.', 'danger')
            paciente_temporal = Paciente(**request.form)
            return render_template('registrar_paciente.html', form_data=request.form, paciente=paciente_temporal)
        try:
            # --- 1. OBTENCIÓN DE DATOS DE TEXTO DEL FORMULARIO ---
            # (Esta parte es larga pero correcta, simplemente toma los valores)
            nombres = request.form.get('nombres')
            apellidos = request.form.get('apellidos')
            tipo_documento = request.form.get('tipo_documento')
            fecha_nacimiento_str = request.form.get('fecha_nacimiento')
            fecha_nacimiento = datetime.strptime(fecha_nacimiento_str, '%Y-%m-%d').date() if fecha_nacimiento_str else None    
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

            # --- 2. NUEVA LÓGICA DE MANEJO DE IMÁGENES CON CLOUDINARY ---
            
            # Obtiene la URL del dentigrama (que ya fue subida por el JS)
            dentigrama_url = request.form.get('dentigrama_url')

            # Inicializa las URLs de las otras imágenes
            imagen_1_url = None
            imagen_2_url = None
            
            # Procesa imagen_1 si fue enviada
            if 'imagen_1_url' in request.files:
                imagen_1_file = request.files['imagen_1_url']
                if imagen_1_file and allowed_file(imagen_1_file.filename):
                    upload_result_1 = cloudinary.uploader.upload(
                        imagen_1_file,
                        folder="paciente_imagenes"  # Carpeta en Cloudinary
                    )
                    imagen_1_url = upload_result_1.get('secure_url')

            # Procesa imagen_2 si fue enviada
            if 'imagen_2_url' in request.files:
                imagen_2_file = request.files['imagen_2_url']
                if imagen_2_file and allowed_file(imagen_2_file.filename):
                    upload_result_2 = cloudinary.uploader.upload(
                        imagen_2_file,
                        folder="paciente_imagenes"  # Carpeta en Cloudinary
                    )
                    imagen_2_url = upload_result_2.get('secure_url')

            # --- 3. CREAR EL OBJETO PACIENTE CON LOS DATOS CORRECTOS ---
            nuevo_paciente = Paciente(
                nombres=nombres,
                apellidos=apellidos,
                tipo_documento=tipo_documento,
                documento=documento,
                fecha_nacimiento=fecha_nacimiento,
                telefono=telefono,
                edad=edad,
                email=email,
                genero=genero,
                estado_civil=estado_civil,
                direccion=direccion,
                barrio=barrio,
                municipio=municipio,
                departamento=departamento,
                aseguradora=aseguradora,
                tipo_vinculacion=tipo_vinculacion,
                ocupacion=ocupacion,
                referido_por=referido_por,
                nombre_responsable=nombre_responsable,
                telefono_responsable=telefono_responsable,
                parentesco=parentesco,
                motivo_consulta=motivo_consulta,
                enfermedad_actual=enfermedad_actual,
                antecedentes_personales=antecedentes_personales,
                antecedentes_familiares=antecedentes_familiares,
                antecedentes_quirurgicos=antecedentes_quirurgicos,
                antecedentes_hemorragicos=antecedentes_hemorragicos,
                farmacologicos=farmacologicos,
                reaccion_medicamentos=reaccion_medicamentos,
                alergias=alergias,
                habitos=habitos,
                cepillado=cepillado,
                examen_fisico=examen_fisico,
                ultima_visita_odontologo=ultima_visita_odontologo,
                plan_tratamiento=plan_tratamiento,
                observaciones=observaciones,
                
                # Nombres de campo actualizados para las URLs de Cloudinary
                dentigrama_url=dentigrama_url,
                imagen_1_url=imagen_1_url,
                imagen_2_url=imagen_2_url,
                
                odontologo_id=current_user.id
            )

            db.session.add(nuevo_paciente)
            db.session.commit()

            flash('Paciente guardado con éxito', 'success')
            return redirect(url_for('pacientes.lista_pacientes'))

        except Exception as e:
            db.session.rollback()
            flash('Ocurrió un error inesperado al guardar el paciente. Por favor, revisa los datos.', 'danger')
            current_app.logger.error(f'Error al guardar paciente: {e}', exc_info=True)
            # 👇 TAMBIÉN NECESITAMOS PASAR EL OBJETO AQUÍ, EN CASO DE ERROR 👇
            paciente_con_error = Paciente(**request.form)
            return render_template('registrar_paciente.html', form_data=request.form, paciente=paciente_con_error)

    # --- 👇 ESTA ES LA LÍNEA PARA EL MÉTODO GET 👇 ---
    # Si no es POST, simplemente crea un paciente vacío y muestra el formulario.
    paciente_vacio = Paciente()
    return render_template('registrar_paciente.html', form_data={}, paciente=paciente_vacio)

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



@pacientes_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_paciente(id):
    query = Paciente.query.filter_by(id=id, is_deleted=False)
    if not current_user.is_admin:
        query = query.filter_by(odontologo_id=current_user.id)
    paciente = query.first_or_404()
    
    if request.method == 'POST':
        try:
            # --- 1. ACTUALIZACIÓN DE DATOS DE TEXTO ---
            # (Toda tu lógica para actualizar nombres, documento, email, etc., está bien y se mantiene)
            paciente.nombres = request.form.get('nombres')
            paciente.apellidos = request.form.get('apellidos')
            paciente.tipo_documento = request.form.get('tipo_documento')
            
            # (Aquí iría tu lógica robusta para validar el documento y el email que ya tenías)
            paciente.documento = request.form.get('documento')
            paciente.email = request.form.get('email')

            paciente.fecha_nacimiento = convertir_a_fecha(request.form.get('fecha_nacimiento', ''))
            paciente.edad = request.form.get('edad', type=int)
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


            if 'eliminar_imagen_1' in request.form and paciente.imagen_1_url:
                public_id = extract_public_id_from_url(paciente.imagen_1_url)
                if public_id: cloudinary.uploader.destroy(public_id)
                paciente.imagen_1_url = None

            if 'eliminar_imagen_2' in request.form and paciente.imagen_2_url:
                public_id = extract_public_id_from_url(paciente.imagen_2_url)
                if public_id: cloudinary.uploader.destroy(public_id)
                paciente.imagen_2_url = None

            # B. Manejo de subida (REEMPLAZO) de nuevas imágenes
            if 'imagen_1_url' in request.files:
                imagen_1_file = request.files['imagen_1_url']
                if imagen_1_file and allowed_file(imagen_1_file.filename):
                    # ▼▼▼ LÓGICA CLAVE: Si ya existía una imagen, bórrala primero ▼▼▼
                    if paciente.imagen_1_url:
                        public_id_antiguo = extract_public_id_from_url(paciente.imagen_1_url)
                        if public_id_antiguo: cloudinary.uploader.destroy(public_id_antiguo)
                    
                    # Sube la nueva imagen
                    upload_result = cloudinary.uploader.upload(imagen_1_file, folder="paciente_imagenes")
                    paciente.imagen_1_url = upload_result.get('secure_url')

            if 'imagen_2_url' in request.files:
                # (misma lógica de borrado y subida para imagen_2)
                imagen_2_file = request.files['imagen_2_url']
                if imagen_2_file and allowed_file(imagen_2_file.filename):
                    if paciente.imagen_2_url:
                        public_id_antiguo = extract_public_id_from_url(paciente.imagen_2_url)
                        if public_id_antiguo: cloudinary.uploader.destroy(public_id_antiguo)
                    upload_result = cloudinary.uploader.upload(imagen_2_file, folder="paciente_imagenes")
                    paciente.imagen_2_url = upload_result.get('secure_url')

            # C. Manejo del Dentigrama (REEMPLAZO)
            dentigrama_url_from_form = request.form.get('dentigrama_url')
            # Si se envió una nueva URL y es diferente a la que ya teníamos...
            if dentigrama_url_from_form and paciente.dentigrama_url != dentigrama_url_from_form:
                # ▼▼▼ LÓGICA CLAVE: Borramos el dentigrama antiguo ▼▼▼
                if paciente.dentigrama_url:
                    public_id_antiguo = extract_public_id_from_url(paciente.dentigrama_url)
                    if public_id_antiguo:
                        cloudinary.uploader.destroy(public_id_antiguo)
                # Actualizamos con la nueva URL
                paciente.dentigrama_url = dentigrama_url_from_form
            # --- 3. MANEJO DE NUEVA EVOLUCIÓN (SIN CAMBIOS) ---
            nueva_evolucion_desc = request.form.get('nueva_evolucion')
            if nueva_evolucion_desc and nueva_evolucion_desc.strip():
                evolucion_obj = Evolucion(descripcion=nueva_evolucion_desc.strip(), paciente_id=paciente.id)
                db.session.add(evolucion_obj)
            
            # --- 4. COMMIT FINAL ---
            db.session.commit()
            flash('Paciente actualizado correctamente', 'success')
            return redirect(url_for('pacientes.mostrar_paciente', id=paciente.id))

        except Exception as e:
            db.session.rollback()
            flash('Ocurrió un error al actualizar el paciente.', 'danger')
            current_app.logger.error(f'Error al editar paciente {id}: {e}', exc_info=True)
            return render_template('editar_paciente.html', paciente=paciente, form_data=request.form)

    # --- LÓGICA PARA EL MÉTODO GET (SIN CAMBIOS) ---
    form_data_inicial = {key: getattr(paciente, key, '') for key in paciente.__table__.columns.keys()}
    if paciente.fecha_nacimiento:
        form_data_inicial['fecha_nacimiento'] = paciente.fecha_nacimiento.strftime('%Y-%m-%d')
    return render_template('editar_paciente.html', paciente=paciente, form_data=form_data_inicial)
# ▼▼▼ ESTA ES LA RUTA NUEVA Y COMPLETA QUE NECESITAS AÑADIR ▼▼▼
@pacientes_bp.route('/upload_dentigrama', methods=['POST'])

def upload_dentigrama():
    # 1. Verificar si el archivo viene en la petición
    if 'dentigrama_overlay' not in request.files:
        # Si no viene, devolvemos un error JSON claro
        return jsonify({'error': 'No se encontró el archivo del dentigrama en la petición'}), 400

    file_to_upload = request.files['dentigrama_overlay']

    # 2. Verificar si el nombre del archivo no está vacío
    if file_to_upload.filename == '':
        return jsonify({'error': 'No se seleccionó ningún archivo'}), 400

    try:
        # 3. Intentar subir el archivo a Cloudinary
        print("Intentando subir archivo a Cloudinary...")
        upload_result = cloudinary.uploader.upload(
            file_to_upload,
            folder="dentigramas_overlay" # Organiza los archivos en una carpeta en Cloudinary
        )
        print("Archivo subido exitosamente.")
        
        # 4. Si todo sale bien, devolver la URL segura en formato JSON
        return jsonify({'url': upload_result['secure_url']})

    except Exception as e:
        # 5. Si algo falla durante la subida, capturar el error y devolverlo
        print(f"Error al subir a Cloudinary: {e}")
        return jsonify({'error': str(e)}), 500