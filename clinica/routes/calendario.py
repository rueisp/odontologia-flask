# clinica/routes/calendario.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from datetime import date, datetime, time, timedelta
import calendar
from ..models import db, Cita, Paciente, AuditLog
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, extract, func, exc as sqlalchemy_exc
from urllib.parse import urlparse, urljoin
import uuid
import os
from flask_login import current_user, login_required
from uuid import uuid4
from ..utils import convertir_a_fecha
from urllib.parse import quote_plus

import pytz # <--- ¡IMPORTANTE: AÑADIR ESTA IMPORTACIÓN!

calendario_bp = Blueprint('calendario', __name__, url_prefix='/calendario')

# --- Nombres de los meses (se mantiene) ---
NOMBRES_MESES_ESP = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

# --- Función de utilidad para URL segura (se mantiene) ---
def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


# --- MODIFICACIÓN: La función construir_dias_del_mes ahora acepta la fecha actual localizada ---
def construir_dias_del_mes(anio, mes, citas_del_mes_obj, dia_hoy_local, mes_hoy_local, anio_hoy_local):
    dias_calendario = []
    primer_dia_obj = date(anio, mes, 1)
    total_dias_en_mes = calendar.monthrange(anio, mes)[1]
    # dia_hoy = date.today() # <--- ELIMINADO: Ya no usamos date.today() aquí

    dia_semana_inicio = (primer_dia_obj.weekday() + 1) % 7

    for _ in range(dia_semana_inicio):
        dias_calendario.append({'fecha': None, 'hoy': False, 'citas': []})

    for dia_num in range(1, total_dias_en_mes + 1):
        fecha_actual_dia = date(anio, mes, dia_num)

        citas_en_dia_actual = [c for c in citas_del_mes_obj if date.fromisoformat(c['fecha']) == fecha_actual_dia]

        citas_preparadas = []
        for cita_dict in citas_en_dia_actual:
            citas_preparadas.append({
                'id': cita_dict['id'],
                'fecha': cita_dict['fecha'],
                'hora': cita_dict['hora'],
                'motivo': cita_dict['motivo'],
                'doctor': cita_dict['doctor'],
                'observaciones': cita_dict['observaciones'],
                'estado': cita_dict['estado'],
                'paciente_id': cita_dict['paciente_id'],
                'paciente_nombre_completo': cita_dict['paciente_nombre_completo'],
                'paciente_telefono_str': cita_dict['paciente_telefono_str'],
                'edit_url': cita_dict['edit_url'],
                'delete_url': cita_dict['delete_url'],
                'next_url_encoded': cita_dict['next_url_encoded']
            })

        # --- MODIFICACIÓN CLAVE: Comparamos con la fecha localizada de "hoy" ---
        es_hoy = (fecha_actual_dia.day == dia_hoy_local and
                  fecha_actual_dia.month == mes_hoy_local and
                  fecha_actual_dia.year == anio_hoy_local)

        dias_calendario.append({
            'fecha': fecha_actual_dia,
            'hoy': es_hoy, # <--- Usamos la nueva variable 'es_hoy'
            'citas': citas_preparadas
        })

    total_celdas_actual = len(dias_calendario)
    celdas_vacias_final = (7 - total_celdas_actual % 7) % 7
    for _ in range(celdas_vacias_final):
        dias_calendario.append({'fecha': None, 'hoy': False, 'citas': []})
    return dias_calendario


@calendario_bp.route('/')
@login_required
def mostrar_calendario():
    # --- MODIFICACIONES CLAVE PARA ZONA HORARIA ---
    # Define la zona horaria de tu clínica
    local_timezone = pytz.timezone('America/Bogota') # <--- CAMBIAR SI TU ZONA HORARIA ES DIFERENTE

    # Obtiene la fecha y hora actuales en esa zona horaria
    now_in_local_tz = datetime.now(local_timezone)

    print(f"DEBUG_CALENDARIO: Hora UTC en el servidor: {datetime.utcnow()}")
    print(f"DEBUG_CALENDARIO: Hora localizada (America/Bogota): {now_in_local_tz}")
    print(f"DEBUG_CALENDARIO: Dia Hoy Local: {now_in_local_tz.day}/{now_in_local_tz.month}/{now_in_local_tz.year}")

    
    # Usa la fecha localizada para determinar los valores predeterminados de anio y mes
    anio_actual = request.args.get('anio', default=now_in_local_tz.year, type=int)
    mes_actual = request.args.get('mes', default=now_in_local_tz.month, type=int)

    # Guarda el día, mes y año de "hoy" en la zona horaria local para marcarlo en el calendario
    dia_hoy_local = now_in_local_tz.day
    mes_hoy_local = now_in_local_tz.month
    anio_hoy_local = now_in_local_tz.year
    # --- FIN MODIFICACIONES CLAVE PARA ZONA HORARIA ---


    try:
        date(anio_actual, mes_actual, 1)
    except ValueError:
        flash("Mes o año inválido.", "warning")
        # Si hay un error, volvemos a la fecha localizada
        anio_actual = now_in_local_tz.year
        mes_actual = now_in_local_tz.month

    query_citas = Cita.query.outerjoin(Paciente, Cita.paciente_id == Paciente.id).options(joinedload(Cita.paciente)).filter(
        Cita.is_deleted == False,
        extract('year', Cita.fecha) == anio_actual,
        extract('month', Cita.fecha) == mes_actual
    )

    if not current_user.is_admin:
        query_citas = query_citas.filter(
            or_(
                Paciente.odontologo_id == current_user.id,
                Cita.paciente_id == None
            )
        )
    else:
        query_citas = query_citas.filter(or_(Paciente.is_deleted == False, Cita.paciente_id == None))

    citas_del_mes = query_citas.order_by(Cita.fecha, Cita.hora).all()

    current_full_path_for_template = request.full_path

    citas_para_construir = []
    for cita_obj in citas_del_mes:
        paciente_nombre_completo = "Paciente sin registrar"
        if cita_obj.paciente and not cita_obj.paciente.is_deleted:
            paciente_nombre_completo = f"{cita_obj.paciente.nombres} {cita_obj.paciente.apellidos}"
        elif cita_obj.paciente_nombres_str and cita_obj.paciente_apellidos_str:
            paciente_nombre_completo = f"{cita_obj.paciente_nombres_str} {cita_obj.paciente_apellidos_str}"
        elif cita_obj.paciente_nombres_str:
            paciente_nombre_completo = cita_obj.paciente_nombres_str

        citas_para_construir.append({
            'id': cita_obj.id,
            'fecha': cita_obj.fecha.strftime('%Y-%m-%d'),
            'hora': cita_obj.hora.strftime('%H:%M'),
            'motivo': cita_obj.motivo,
            'doctor': cita_obj.doctor,
            'observaciones': cita_obj.observaciones,
            'estado': cita_obj.estado,
            'paciente_id': cita_obj.paciente_id,
            'paciente_nombre_completo': paciente_nombre_completo,
            'paciente_telefono_str': cita_obj.paciente_telefono_str,
            'edit_url': url_for('calendario.editar_cita', cita_id=cita_obj.id, next=current_full_path_for_template),
            'delete_url': url_for('calendario.eliminar_cita', cita_id=cita_obj.id, next=current_full_path_for_template),
            'next_url_encoded': quote_plus(current_full_path_for_template)
        })

    # --- MODIFICACIÓN: Pasamos los valores de "hoy" a construir_dias_del_mes ---
    dias_render = construir_dias_del_mes(anio_actual, mes_actual, citas_para_construir,
                                         dia_hoy_local, mes_hoy_local, anio_hoy_local) # <--- AÑADIDO
    nombre_mes_actual_display = NOMBRES_MESES_ESP[mes_actual-1]

    return render_template('calendario.html',
                           anio=anio_actual,
                           mes=mes_actual,
                           nombres_meses=NOMBRES_MESES_ESP,
                           nombre_mes_display=nombre_mes_actual_display,
                           dias=dias_render,
                           # --- MODIFICACIÓN: Pasamos los valores de "hoy" localizados a la plantilla ---
                           anio_hoy=anio_hoy_local,
                           mes_hoy=mes_hoy_local,
                           dia_hoy=dia_hoy_local, # <--- AÑADIDO
                           current_full_path=current_full_path_for_template)


@calendario_bp.route('/registrar_cita', methods=['GET', 'POST'])
@login_required 
def registrar_cita(): 
    next_url_get = request.args.get('next')
    fecha_preseleccionada_str = request.args.get('fecha') if request.method == 'GET' else None
    
    form_values = {
        'paciente_preseleccionado_id': '', # Nuevo campo para pasar el ID precargado al HTML
        'paciente_preseleccionado_nombre': '', # Nuevo campo para pasar el nombre precargado al HTML
        'paciente_nombres_val': '', 'paciente_apellidos_val': '', 'paciente_edad_val': '',
        'paciente_documento_val': '', 'paciente_telefono_val': '',
        'fecha_val': fecha_preseleccionada_str or '', 'hora_val': '',
        'doctor_val': '', 'motivo_val': '', 'observaciones_val': '',
        'next_url': next_url_get or '',
    }

    # Si se viene de un perfil de paciente (GET), preseleccionar ese paciente
    paciente_id_param = request.args.get('paciente_id_param', type=int) # Leer el ID si viene de URL
    if request.method == 'GET' and paciente_id_param:
        paciente_precargado = Paciente.query.filter_by(id=paciente_id_param, is_deleted=False).first()
        if paciente_precargado:
            form_values['paciente_preseleccionado_id'] = paciente_precargado.id
            form_values['paciente_preseleccionado_nombre'] = f"{paciente_precargado.nombres} {paciente_precargado.apellidos}"
            form_values['paciente_nombres_val'] = paciente_precargado.nombres
            form_values['paciente_apellidos_val'] = paciente_precargado.apellidos
            form_values['paciente_edad_val'] = paciente_precargado.edad
            form_values['paciente_documento_val'] = paciente_precargado.documento
            form_values['paciente_telefono_val'] = paciente_precargado.telefono


    if request.method == 'POST':
        try:
            current_next_url = request.form.get('next') or next_url_get or ''
            
            # --- OBTENER ID DE PACIENTE SELECCIONADO DEL BUSCADOR (oculto) ---
            paciente_id_seleccionado = request.form.get('paciente_id', type=int) 
            
            # --- OBTENER DATOS DE CAMPOS MANUALES (para crear nueva cita o si no hay paciente_id) ---
            nombres_pac_form = request.form.get('paciente_nombres_str', '').strip() # NOMBRE CORREGIDO
            apellidos_pac_form = request.form.get('paciente_apellidos_str', '').strip() # NOMBRE CORREGIDO
            # edad_pac_str = request.form.get('paciente_edad_val', '').strip() # No se guarda en Cita, pero lo puedes usar para validación si crearas Paciente
            # documento_pac_form = request.form.get('paciente_documento_val', '').strip() # No se guarda en Cita
            telefono_pac_form = request.form.get('paciente_telefono_str', '').strip() # NOMBRE CORREGIDO

            fecha_str = request.form.get('fecha')
            hora_str = request.form.get('hora')
            doctor_form = request.form.get('doctor', '').strip()
            motivo_form = request.form.get('motivo', '').strip()
            observaciones_form = request.form.get('observaciones', '').strip()

            # Rellenar form_values para re-renderizar si hay errores
            form_values.update({
                'paciente_preseleccionado_id': paciente_id_seleccionado, # Mantener el ID seleccionado
                'paciente_preseleccionado_nombre': request.form.get('paciente_busqueda_input', ''), # También el nombre visible del buscador
                'paciente_nombres_val': nombres_pac_form, 
                'paciente_apellidos_val': apellidos_pac_form,
                # 'paciente_edad_val': edad_pac_str, # Si se usan en el futuro
                # 'paciente_documento_val': documento_pac_form,
                'paciente_telefono_val': telefono_pac_form,
                'fecha_val': fecha_str, 'hora_val': hora_str, 'doctor_val': doctor_form,
                'motivo_val': motivo_form, 'observaciones_val': observaciones_form
            })

            # --- Validaciones de la Cita (Campos Obligatorios) ---
            # Si hay un paciente_id, no necesitamos nombres/apellidos_str requeridos
            if not paciente_id_seleccionado and not (nombres_pac_form and apellidos_pac_form and telefono_pac_form):
                 flash("Nombres, Apellidos y Teléfono del paciente son obligatorios si no se selecciona un paciente existente.", "error")
                 return render_template('registrar_cita.html', form_values=form_values)

            # Validaciones para fecha, hora y doctor, siempre requeridos
            if not (fecha_str and hora_str and doctor_form):
                flash("Fecha, Hora y Doctor son campos obligatorios para la cita.", "error")
                return render_template('registrar_cita.html', form_values=form_values)
            
            try:
                fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
                hora_obj = datetime.strptime(hora_str, "%H:%M").time()
            except ValueError:
                flash("Formato de fecha u hora inválido.", "error")
                return render_template('registrar_cita.html', form_values=form_values)
            
            nueva_cita = Cita(
                fecha=fecha_obj,
                hora=hora_obj,
                doctor=doctor_form,
                motivo=motivo_form or None,
                observaciones=observaciones_form or None,
                # Inicializar paciente_id y campos string como None
                paciente_id=None,
                paciente_nombres_str=None,
                paciente_apellidos_str=None,
                paciente_telefono_str=None,
            )

            # --- Lógica para asignar paciente a la cita ---
            if paciente_id_seleccionado:
                paciente_existente = Paciente.query.filter_by(id=paciente_id_seleccionado, is_deleted=False).first()
                if paciente_existente:
                    nueva_cita.paciente_id = paciente_existente.id
                else:
                    flash("El paciente seleccionado no es válido o ha sido eliminado.", "error")
                    return render_template('registrar_cita.html', form_values=form_values)
            else:
                # Si no se seleccionó un paciente, usar los datos manuales para la cita
                nueva_cita.paciente_nombres_str = nombres_pac_form
                nueva_cita.paciente_apellidos_str = apellidos_pac_form
                nueva_cita.paciente_telefono_str = telefono_pac_form
            # --- FIN Lógica de asignación de paciente ---
            
            db.session.add(nueva_cita)
            db.session.commit() 

            flash("Cita registrada correctamente.", "success")
            
            redirect_url = current_next_url 
            if redirect_url and is_safe_url(redirect_url):
                return redirect(redirect_url)
            return redirect(url_for('.mostrar_calendario', anio=fecha_obj.year, mes=fecha_obj.month))

        except Exception as e: 
            db.session.rollback()
            flash(f"Ocurrió un error inesperado al guardar la cita: {str(e)}", "error")
            current_app.logger.error(f"Error detallado al guardar cita: {e}", exc_info=True)
            return render_template('registrar_cita.html', form_values=form_values)

    return render_template('registrar_cita.html', 
                           form_values=form_values, 
                           pacientes=Paciente.query.filter_by(is_deleted=False).order_by(Paciente.apellidos).all()) # Ya no se usa la lista 'pacientes' en el template. Puedes quitarla.
# --- FUNCIÓN EDITAR CITA ---
@calendario_bp.route('/editar_cita/<int:cita_id>', methods=['GET', 'POST'])
@login_required 
def editar_cita(cita_id):
    cita_obj = Cita.query.options(joinedload(Cita.paciente)).get_or_404(cita_id)

    if not current_user.is_admin and cita_obj.paciente and cita_obj.paciente.odontologo_id != current_user.id:
        flash("Acceso denegado. No tienes permiso para editar esta cita.", "danger")
        return redirect(url_for('.mostrar_calendario')) 
    
    # Si la cita no tiene paciente_id, cita_obj.paciente será None.
    # Necesitamos proteger el acceso a cita_obj.paciente.odontologo_id si es None.
    # La condición anterior `cita_obj.paciente and ...` ya lo hace.

    query_pacientes_para_dropdown = Paciente.query.filter_by(is_deleted=False)
    if not current_user.is_admin:
        query_pacientes_para_dropdown = query_pacientes_para_dropdown.filter_by(odontologo_id=current_user.id)
    todos_los_pacientes = query_pacientes_para_dropdown.order_by(Paciente.apellidos, Paciente.nombres).all()
    
    next_url_get = request.args.get('next')
    
    form_data_edit = {
        'selected_paciente_id': str(cita_obj.paciente_id) if cita_obj.paciente_id else '', # Asegurarse de que sea string o vacío
        'fecha_val': cita_obj.fecha.strftime('%Y-%m-%d'),
        'hora_val': cita_obj.hora.strftime('%H:%M'),
        'doctor_val': cita_obj.doctor,
        'motivo_val': cita_obj.motivo or '',
        'observaciones_val': cita_obj.observaciones or '',
        'next_url': next_url_get
    }

    if request.method == 'POST':
        current_next_url = request.form.get('next') or next_url_get
        form_data_edit['next_url'] = current_next_url 

        paciente_id_form = request.form.get('paciente_id') # No forzar a int todavía
        fecha_str = request.form.get('fecha')
        hora_str = request.form.get('hora')
        doctor_form = request.form.get('doctor')
        motivo_form = request.form.get('motivo')
        observaciones_form = request.form.get('observaciones')
        
        # --- VERIFICACIÓN DE SEGURIDAD ADICIONAL EN POST ---
        if paciente_id_form and not current_user.is_admin: # Solo verificar si se proporcionó un paciente_id
            paciente_destino = Paciente.query.filter_by(id=int(paciente_id_form), odontologo_id=current_user.id, is_deleted=False).first()
            if not paciente_destino:
                flash("Error: Se intentó asignar la cita a un paciente que no te pertenece o no existe.", "danger")
                return render_template('editar_cita.html', cita=cita_obj, pacientes=todos_los_pacientes, form_data=form_data_edit)
        # --- FIN VERIFICACIÓN POST ---
        
        form_data_edit.update({
            'selected_paciente_id': paciente_id_form, 'fecha_val': fecha_str, 'hora_val': hora_str,
            'doctor_val': doctor_form, 'motivo_val': motivo_form, 'observaciones_val': observaciones_form
        })

        if not (fecha_str and hora_str and doctor_form): # paciente_id_form ya no es obligatorio
            flash("Fecha, hora y doctor son campos obligatorios.", "error")
            return render_template('editar_cita.html', cita=cita_obj, pacientes=todos_los_pacientes, form_data=form_data_edit)

        try:
            cita_obj.paciente_id = int(paciente_id_form) if paciente_id_form else None # Aceptar None
            cita_obj.fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            cita_obj.hora = datetime.strptime(hora_str, "%H:%M").time()
        except ValueError:
            flash("Formato de fecha u hora inválido.", "error")
            return render_template('editar_cita.html', cita=cita_obj, pacientes=todos_los_pacientes, form_data=form_data_edit)

        cita_obj.doctor = doctor_form
        cita_obj.motivo = motivo_form or None
        cita_obj.observaciones = observaciones_form or None

        try:
            db.session.commit()
            flash("Cita actualizada correctamente.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error al actualizar la cita: {e}", "error")
            current_app.logger.error(f"Error detallado al editar cita: {e}", exc_info=True)
            return render_template('editar_cita.html', cita=cita_obj, pacientes=todos_los_pacientes, form_data=form_data_edit)

        if form_data_edit['next_url'] and is_safe_url(form_data_edit['next_url']):
            return redirect(form_data_edit['next_url'])
        return redirect(url_for('.mostrar_calendario', anio=cita_obj.fecha.year, mes=cita_obj.fecha.month))

    return render_template('editar_cita.html', cita=cita_obj, pacientes=todos_los_pacientes, form_data=form_data_edit)


# --- NUEVA RUTA: Historial de Citas por Paciente ---
@calendario_bp.route('/historial_citas_paciente/<int:paciente_id>', methods=['GET'])
@login_required
def historial_citas_paciente(paciente_id):
    # 1. Verificar si el paciente existe y si el usuario tiene permisos
    paciente = Paciente.query.filter_by(id=paciente_id, is_deleted=False).first_or_404()

    if not current_user.is_admin and paciente.odontologo_id != current_user.id:
        flash("Acceso denegado. No tienes permiso para ver el historial de este paciente.", "danger")
        return redirect(url_for('pacientes.lista_pacientes'))

    # 2. Obtener todas las citas (no eliminadas) para este paciente, ordenadas por fecha y hora
    citas = Cita.query.filter(
        Cita.paciente_id == paciente_id,
        Cita.is_deleted == False
    ).order_by(Cita.fecha.desc(), Cita.hora.desc()).all()

    # 3. Preparar los datos de las citas para el template
    citas_procesadas = []
    for cita_obj in citas:
        # Aquí puedes formatear cualquier dato adicional que necesites en el template
        citas_procesadas.append({
            'id': cita_obj.id,
            'fecha': cita_obj.fecha.strftime('%d/%m/%Y'),
            'hora': cita_obj.hora.strftime('%H:%M'),
            'motivo': cita_obj.motivo or 'No especificado',
            'doctor': cita_obj.doctor or 'N/A',
            'observaciones': cita_obj.observaciones or '',
            'estado': cita_obj.estado or 'Pendiente',
            'edit_url': url_for('calendario.editar_cita', cita_id=cita_obj.id, next=request.full_path),
            'delete_url': url_for('calendario.eliminar_cita', cita_id=cita_obj.id, next=request.full_path),
        })

    return render_template('historial_citas_paciente.html', 
                           paciente=paciente, 
                           citas=citas_procesadas)


# --- FUNCIÓN ELIMINAR CITA ---
@calendario_bp.route('/eliminar_cita/<int:cita_id>', methods=['POST'])
@login_required 
def eliminar_cita(cita_id):
    cita_a_mover_papelera = Cita.query.options(joinedload(Cita.paciente)).get_or_404(cita_id)
    
    if not current_user.is_admin and cita_a_mover_papelera.paciente.odontologo_id != current_user.id:
        flash("Acceso denegado. No tienes permiso para eliminar esta cita.", "danger")
        return redirect(url_for('.mostrar_calendario'))
    
    if cita_a_mover_papelera.is_deleted:
        flash('Esta cita ya se encuentra en la papelera.', 'info')
        next_url_fallback = url_for('.mostrar_calendario', 
                                    anio=cita_a_mover_papelera.fecha.year, 
                                    mes=cita_a_mover_papelera.fecha.month)
        if cita_a_mover_papelera.paciente_id:
            next_url_fallback = url_for('pacientes.mostrar_paciente', id=cita_a_mover_papelera.paciente_id) 
        return redirect(request.form.get('next') or next_url_fallback)

    paciente_nombre_log = "Desconocido"
    if cita_a_mover_papelera.paciente: 
        paciente_nombre_log = f"{cita_a_mover_papelera.paciente.nombres} {cita_a_mover_papelera.paciente.apellidos}"
    
    log_descripcion_detalle = (
        f"Cita (ID: {cita_a_mover_papelera.id}) "
        f"para el paciente '{paciente_nombre_log}' (Paciente ID: {cita_a_mover_papelera.paciente_id}) "
        f"del {cita_a_mover_papelera.fecha.strftime('%d/%m/%Y')} a las {cita_a_mover_papelera.hora.strftime('%H:%M')} "
        f"con Dr(a). {cita_a_mover_papelera.doctor or 'N/A'}. Motivo: {cita_a_mover_papelera.motivo or 'No especificado'}."
    )
    cita_id_para_log = cita_a_mover_papelera.id
    
    next_url = request.form.get('next') 
    anio_cita_fallback = cita_a_mover_papelera.fecha.year
    mes_cita_fallback = cita_a_mover_papelera.fecha.month
    paciente_id_fallback = cita_a_mover_papelera.paciente_id


    try:
        cita_a_mover_papelera.is_deleted = True
        cita_a_mover_papelera.deleted_at = datetime.utcnow()

        audit_entry = AuditLog(
            action_type="SOFT_DELETE_CITA", 
            description=f"Cita movida a la papelera: {log_descripcion_detalle}",
            target_model="Cita",
            target_id=cita_id_para_log,
        )
        
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            audit_entry.user_id = current_user.id
            audit_entry.user_username = current_user.username 
        else:
            audit_entry.user_username = "Sistema/Desconocido"

        db.session.add(audit_entry) 
        
        db.session.commit() 
        
        flash("Cita movida a la papelera y acción registrada.", "success")

    except Exception as e:
        db.session.rollback() 
        flash(f"Error al mover la cita a la papelera: {str(e)}", "error")
        current_app.logger.error(f"Error detallado al mover cita ID {cita_id} a la papelera o registrar auditoría: {e}", exc_info=True)

    if next_url and is_safe_url(next_url):
        return redirect(next_url)
    
    if paciente_id_fallback:
        try:
            return redirect(url_for('pacientes.mostrar_paciente', id=paciente_id_fallback))
        except Exception: 
            current_app.logger.warning(f"No se pudo redirigir a la vista del paciente {paciente_id_fallback}, yendo al calendario.")
            pass 
            
    return redirect(url_for('.mostrar_calendario', anio=anio_cita_fallback, mes=mes_cita_fallback))


# --- FUNCIÓN ACTUALIZAR ESTADO CITA ---
@calendario_bp.route('/cita/actualizar_estado/<int:cita_id>', methods=['POST'])
@login_required 
def actualizar_estado_cita(cita_id):
    cita = Cita.query.get(cita_id)

    if not cita:
        return jsonify({'success': False, 'message': 'Cita no encontrada.'}), 404
    
    if not current_user.is_admin:
        if cita.paciente and cita.paciente.odontologo_id != current_user.id:
            current_app.logger.warning(f"Intento de actualizar cita {cita_id} de paciente {cita.paciente_id} por usuario no autorizado {current_user.id}.")
            return jsonify({'success': False, 'message': 'No tienes permiso para actualizar el estado de esta cita.'}), 403 

    data = request.get_json()
    if not data or 'estado' not in data:
        return jsonify({'success': False, 'message': 'No se proporcionó el nuevo estado.'}), 400

    nuevo_estado = data.get('estado')
    estados_validos = ['pendiente', 'completada', 'cancelada', 'confirmada', 'reprogramada', 'no_asistio']

    if nuevo_estado not in estados_validos:
        return jsonify({'success': False, 'message': f"Estado '{nuevo_estado}' no válido."}), 400

    try:
        cita.estado = nuevo_estado
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Estado de la cita actualizado correctamente.',
            'nuevo_estado': nuevo_estado, 
            'cita_id': cita_id
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al actualizar estado de cita ID {cita_id} a '{nuevo_estado}': {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Ocurrió un error al actualizar el estado de la cita.'}), 500