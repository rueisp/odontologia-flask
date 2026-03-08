# clinica/routes/calendario.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from datetime import date, datetime, time, timedelta
import calendar
from ..models import db, Cita, Paciente, AuditLog
from sqlalchemy.orm import joinedload, load_only
from sqlalchemy import or_, extract, func, exc as sqlalchemy_exc, and_
from urllib.parse import urlparse, urljoin
import uuid
import os
from flask_login import current_user, login_required
from uuid import uuid4
from ..utils import convertir_a_fecha
from urllib.parse import quote_plus
from clinica.campos_activos import CAMPOS_PACIENTE_ACTIVOS
import pytz  # <-- important import

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
    # dia_hoy = date.today()  # <-- eliminado

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
        es_hoy = (fecha_actual_dia.day == dia_hoy_local and
                  fecha_actual_dia.month == mes_hoy_local and
                  fecha_actual_dia.year == anio_hoy_local)
        dias_calendario.append({
            'fecha': fecha_actual_dia,
            'hoy': es_hoy,
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
    # Zona horaria local
    local_timezone = pytz.timezone('America/Bogota')
    now_in_local_tz = datetime.now(local_timezone)
    # Parámetros año/mes con defaults basados en zona horaria
    anio_actual = request.args.get('anio', default=now_in_local_tz.year, type=int)
    mes_actual = request.args.get('mes', default=now_in_local_tz.month, type=int)
    # Día de hoy en zona local
    dia_hoy_local = now_in_local_tz.day
    mes_hoy_local = now_in_local_tz.month
    anio_hoy_local = now_in_local_tz.year

    try:
        date(anio_actual, mes_actual, 1)
    except ValueError:
        flash("Mes o año inválido.", "warning")
        anio_actual = now_in_local_tz.year
        mes_actual = now_in_local_tz.month

    # Consulta base de citas
    query_citas = Cita.query.options(
        load_only(
            Cita.id,
            Cita.paciente_id,
            Cita.fecha,
            Cita.hora,
            Cita.motivo,
            Cita.doctor,
            Cita.estado,
            Cita.observaciones,
            Cita.paciente_nombres_str,
            Cita.paciente_apellidos_str,
            Cita.paciente_telefono_str
        )
    ).filter(
        Cita.is_deleted == False,
        extract('year', Cita.fecha) == anio_actual,
        extract('month', Cita.fecha) == mes_actual
    )
    
    # Filtrar por permisos SIN usar Paciente directamente
    if not current_user.is_admin:
        # Obtener IDs de pacientes del usuario actual
        from ..models import Paciente
        paciente_ids_subq = db.session.query(Paciente.id).filter(
            Paciente.odontologo_id == current_user.id,
            Paciente.is_deleted == False
        ).subquery()
        
        query_citas = query_citas.filter(
            or_(
                Cita.paciente_id.in_(paciente_ids_subq),
                Cita.paciente_id == None
            )
        )
    else:
        # Admin ve todas las citas, pero excluimos las de pacientes eliminados
        from ..models import Paciente
        query_citas = query_citas.outerjoin(
            Paciente, Cita.paciente_id == Paciente.id
        ).filter(
            or_(
                Paciente.is_deleted == False,
                Cita.paciente_id == None
            )
        )

    citas_del_mes = query_citas.order_by(Cita.fecha, Cita.hora).all()
    current_full_path_for_template = request.full_path

    # Procesar citas para el template
    citas_para_construir = []
    for cita_obj in citas_del_mes:
        paciente_nombre_completo = "Paciente sin registrar"
        
        # Intentar obtener el paciente de la base de datos si existe
        if cita_obj.paciente_id:
            from ..models import Paciente
            paciente = Paciente.query.get(cita_obj.paciente_id)
            if paciente and not paciente.is_deleted:
                paciente_nombre_completo = f"{paciente.nombres} {paciente.apellidos}"
            else:
                if cita_obj.paciente_nombres_str and cita_obj.paciente_apellidos_str:
                    paciente_nombre_completo = f"{cita_obj.paciente_nombres_str} {cita_obj.paciente_apellidos_str}"
                elif cita_obj.paciente_nombres_str:
                    paciente_nombre_completo = cita_obj.paciente_nombres_str
        else:
            if cita_obj.paciente_nombres_str and cita_obj.paciente_apellidos_str:
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

    dias_render = construir_dias_del_mes(anio_actual, mes_actual, citas_para_construir,
                                         dia_hoy_local, mes_hoy_local, anio_hoy_local)
    nombre_mes_actual_display = NOMBRES_MESES_ESP[mes_actual-1]

    return render_template('calendario.html',
                           anio=anio_actual,
                           mes=mes_actual,
                           nombres_meses=NOMBRES_MESES_ESP,
                           nombre_mes_display=nombre_mes_actual_display,
                           dias=dias_render,
                           anio_hoy=anio_hoy_local,
                           mes_hoy=mes_hoy_local,
                           dia_hoy=dia_hoy_local,
                           current_full_path=current_full_path_for_template)

@calendario_bp.route('/registrar_cita', methods=['GET', 'POST'])
@login_required
def registrar_cita():
    next_url_get = request.args.get('next')
    fecha_preseleccionada_str = request.args.get('fecha') if request.method == 'GET' else None
    hora_preseleccionada_str = request.args.get('hora') if request.method == 'GET' else None  # ← NUEVO
    form_values = {
        'paciente_preseleccionado_id': '',
        'paciente_preseleccionado_nombre': '',
        'paciente_nombres_val': '', 'paciente_apellidos_val': '', 'paciente_edad_val': '',
        'paciente_documento_val': '', 'paciente_telefono_val': '',
        'fecha_val': fecha_preseleccionada_str or '', 'hora_val': '',
        'hora_val': hora_preseleccionada_str or '',  # ← NUEVO
        'doctor_val': '', 'motivo_val': '', 'observaciones_val': '',
        'next_url': next_url_get or '',
    }
    paciente_id_param = request.args.get('paciente_id_param', type=int)
    if request.method == 'GET' and paciente_id_param:
        paciente_precargado = Paciente.query.filter_by(id=paciente_id_param, is_deleted=False).first()
        if paciente_precargado:
            form_values.update({
                'paciente_preseleccionado_id': paciente_precargado.id,
                'paciente_preseleccionado_nombre': f"{paciente_precargado.nombres} {paciente_precargado.apellidos}",
                'paciente_nombres_val': paciente_precargado.nombres,
                'paciente_apellidos_val': paciente_precargado.apellidos,
                'paciente_edad_val': paciente_precargado.edad,
                'paciente_documento_val': paciente_precargado.documento,
                'paciente_telefono_val': paciente_precargado.telefono,
            })
    if request.method == 'POST':
        try:
            current_next_url = request.form.get('next') or next_url_get or ''
            paciente_id_seleccionado = request.form.get('paciente_id', type=int)
            nombres_pac_form = request.form.get('paciente_nombres_str', '').strip()
            apellidos_pac_form = request.form.get('paciente_apellidos_str', '').strip()
            telefono_pac_form = request.form.get('paciente_telefono_str', '').strip()
            fecha_str = request.form.get('fecha')
            hora_str = request.form.get('hora')
            doctor_form = request.form.get('doctor', '').strip()
            motivo_form = request.form.get('motivo', '').strip()
            observaciones_form = request.form.get('observaciones', '').strip()
            form_values.update({
                'paciente_preseleccionado_id': paciente_id_seleccionado,
                'paciente_preseleccionado_nombre': request.form.get('paciente_busqueda_input', ''),
                'paciente_nonueva_cita = Citambres_val': nombres_pac_form,
                'paciente_apellidos_val': apellidos_pac_form,
                'paciente_telefono_val': telefono_pac_form,
                'fecha_val': fecha_str, 'hora_val': hora_str, 'doctor_val': doctor_form,
                'motivo_val': motivo_form, 'observaciones_val': observaciones_form
            })
            if not paciente_id_seleccionado and not (nombres_pac_form and apellidos_pac_form and telefono_pac_form):
                flash("Nombres, Apellidos y Teléfono del paciente son obligatorios si no se selecciona un paciente existente.", "error")
                return render_template('registrar_cita.html', form_values=form_values)
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
                odontologo_id=current_user.id,  # <--- ¡ESTO ES LO QUE FALTABA!
                paciente_id=None,
                paciente_nombres_str=None,
                paciente_apellidos_str=None,
                paciente_telefono_str=None,
            )
            if paciente_id_seleccionado:
                paciente_existente = Paciente.query.filter_by(id=paciente_id_seleccionado, is_deleted=False).first()
                if paciente_existente:
                    nueva_cita.paciente_id = paciente_existente.id
                else:
                    flash("El paciente seleccionado no es válido o ha sido eliminado.", "error")
                    return render_template('registrar_cita.html', form_values=form_values)
            else:
                nueva_cita.paciente_nombres_str = nombres_pac_form
                nueva_cita.paciente_apellidos_str = apellidos_pac_form
                nueva_cita.paciente_telefono_str = telefono_pac_form
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
    return render_template('registrar_cita.html', form_values=form_values)

@calendario_bp.route('/editar_cita/<int:cita_id>', methods=['GET', 'POST'])
@login_required
def editar_cita(cita_id):
    cita_obj = Cita.query.get_or_404(cita_id)
    if not current_user.is_admin and cita_obj.paciente_id:
        paciente = Paciente.query.get(cita_obj.paciente_id)
        if paciente and paciente.odontologo_id != current_user.id:
            flash("Acceso denegado. No tienes permiso para editar esta cita.", "danger")
            return redirect(url_for('.mostrar_calendario'))
    query_pacientes_para_dropdown = Paciente.query.filter_by(is_deleted=False)
    if not current_user.is_admin:
        query_pacientes_para_dropdown = query_pacientes_para_dropdown.filter_by(odontologo_id=current_user.id)
    todos_los_pacientes = query_pacientes_para_dropdown.order_by(Paciente.apellidos, Paciente.nombres).all()
    next_url_get = request.args.get('next')
    form_data_edit = {
        'selected_paciente_id': str(cita_obj.paciente_id) if cita_obj.paciente_id else '',
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
        paciente_id_form = request.form.get('paciente_id')
        fecha_str = request.form.get('fecha')
        hora_str = request.form.get('hora')
        doctor_form = request.form.get('doctor')
        motivo_form = request.form.get('motivo')
        observaciones_form = request.form.get('observaciones')
        if paciente_id_form and not current_user.is_admin:
            paciente_destino = Paciente.query.filter_by(id=int(paciente_id_form), odontologo_id=current_user.id, is_deleted=False).first()
            if not paciente_destino:
                flash("Error: Se intentó asignar la cita a un paciente que no te pertenece o no existe.", "danger")
                return render_template('editar_cita.html', cita=cita_obj, pacientes=todos_los_pacientes, form_data=form_data_edit)
        form_data_edit.update({
            'selected_paciente_id': paciente_id_form,
            'fecha_val': fecha_str,
            'hora_val': hora_str,
            'doctor_val': doctor_form,
            'motivo_val': motivo_form,
            'observaciones_val': observaciones_form
        })
        if not (fecha_str and hora_str and doctor_form):
            flash("Fecha, hora y doctor son campos obligatorios.", "error")
            return render_template('editar_cita.html', cita=cita_obj, pacientes=todos_los_pacientes, form_data=form_data_edit)
        try:
            cita_obj.paciente_id = int(paciente_id_form) if paciente_id_form else None
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

# --- RUTA: Historial de Citas por Paciente (CON MODIFICACIONES) ---
@calendario_bp.route('/historial_citas_paciente/<int:paciente_id>', methods=['GET'])
@login_required
def historial_citas_paciente(paciente_id):
    paciente = Paciente.query.filter_by(id=paciente_id, is_deleted=False).first_or_404()
    if not current_user.is_admin and paciente.odontologo_id != current_user.id:
        flash("Acceso denegado...", "danger")
        return redirect(url_for('pacientes.lista_pacientes'))
    citas_query = Cita.query.filter(
        Cita.paciente_id == paciente_id,
        Cita.is_deleted == False
    ).order_by(Cita.fecha.desc(), Cita.hora.desc())
    citas_del_paciente = citas_query.all()
    hay_citas_pendientes = db.session.query(
        Cita.query.filter_by(paciente_id=paciente_id, factura_id=None, is_deleted=False).exists()
    ).scalar()
    citas_procesadas = []
    for cita_obj in citas_del_paciente:
        citas_procesadas.append({
            'id': cita_obj.id,
            'fecha': cita_obj.fecha.strftime('%d/%m/%Y'),
            'hora': cita_obj.hora.strftime('%H:%M'),
            'motivo': cita_obj.motivo or 'No especificado',
            'doctor': cita_obj.doctor or 'N/A',
            'observaciones': cita_obj.observaciones or '',
            'estado': cita_obj.estado or 'Pendiente',
            'factura_id': cita_obj.factura_id,
            'edit_url': url_for('calendario.editar_cita', cita_id=cita_obj.id, next=request.full_path),
            'delete_url': url_for('calendario.eliminar_cita', cita_id=cita_obj.id, next=request.full_path),
        })
    return render_template('historial_citas_paciente.html',
                           paciente=paciente,
                           citas=citas_procesadas,
                           hay_citas_pendientes=hay_citas_pendientes)

# --- FUNCIÓN ELIMINAR CITA (CORREGIDA) ---
@calendario_bp.route('/eliminar_cita/<int:cita_id>', methods=['POST'])
@login_required
def eliminar_cita(cita_id):
    cita_a_mover_papelera = Cita.query.get_or_404(cita_id)
    
    # Verificar permisos
    if not current_user.is_admin and cita_a_mover_papelera.paciente_id:
        paciente = Paciente.query.get(cita_a_mover_papelera.paciente_id)
        if paciente and paciente.odontologo_id != current_user.id:
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
    
    # Obtener nombre del paciente para el log
    paciente_nombre_log = "Desconocido"
    if cita_a_mover_papelera.paciente_id:
        paciente = Paciente.query.get(cita_a_mover_papelera.paciente_id)
        if paciente:
            paciente_nombre_log = f"{paciente.nombres} {paciente.apellidos}"
    elif cita_a_mover_papelera.paciente_nombres_str:
        paciente_nombre_log = f"{cita_a_mover_papelera.paciente_nombres_str} {cita_a_mover_papelera.paciente_apellidos_str or ''}".strip()
    
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
        cita_a_mover_papelera.deleted_at = datetime.now(pytz.timezone('America/Bogota'))
        
        audit_entry = AuditLog(
            action_type="SOFT_DELETE_CITA",
            description=f"Cita movida a la papelera: {log_descripcion_detalle}",
            target_model="Cita",
            target_id=cita_id_para_log,
            user_id=current_user.id if current_user.is_authenticated else None,
            user_username=current_user.username if current_user.is_authenticated else "Sistema/Desconocido"
        )
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
    
@calendario_bp.route('/dia', methods=['GET'])
@login_required
def vista_diaria():
    from datetime import time, timedelta, datetime, date
    from sqlalchemy.orm import load_only
    
    # Obtener fecha de la URL o usar hoy
    fecha_str = request.args.get('fecha')
    if fecha_str:
        try:
            fecha_seleccionada = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            fecha_seleccionada = date.today()
    else:
        fecha_seleccionada = date.today()
    
    # CONSULTA OPTIMIZADA - SOLO los campos necesarios
    query_citas = Cita.query.options(
        load_only(
            Cita.id, 
            Cita.paciente_id, 
            Cita.fecha, 
            Cita.hora, 
            Cita.motivo, 
            Cita.doctor, 
            Cita.estado,
            Cita.paciente_nombres_str,
            Cita.paciente_apellidos_str,
            Cita.paciente_telefono_str
        )
    ).filter(
        Cita.fecha == fecha_seleccionada,
        Cita.is_deleted == False
    )
    
    # Cargar pacientes relacionados por separado (MUCHO MÁS RÁPIDO)
    citas_del_dia = query_citas.all()
    paciente_ids = list(set([c.paciente_id for c in citas_del_dia if c.paciente_id]))
    
    # Obtener SOLO los datos de pacientes que necesitamos
    pacientes_dict = {}
    if paciente_ids:
        pacientes = Paciente.query.options(
            load_only(
                Paciente.id,
                Paciente.nombres,
                Paciente.apellidos,
                Paciente.telefono
            )
        ).filter(Paciente.id.in_(paciente_ids)).all()
        
        for p in pacientes:
            pacientes_dict[p.id] = p
    
    # Organizar citas por hora
    citas_por_hora = {}
    for cita in citas_del_dia:
        hora_key = cita.hora.strftime('%H:%M')
        
        # Obtener datos del paciente (de la caché o de los campos guardados)
        if cita.paciente_id and cita.paciente_id in pacientes_dict:
            paciente = pacientes_dict[cita.paciente_id]
            paciente_nombre = paciente.nombres or ''
            paciente_apellidos = paciente.apellidos or ''
            paciente_telefono = paciente.telefono or ''
        else:
            paciente_nombre = cita.paciente_nombres_str or ''
            paciente_apellidos = cita.paciente_apellidos_str or ''
            paciente_telefono = cita.paciente_telefono_str or ''
        
        # Verificar permisos
        if not current_user.is_admin:
            if cita.paciente_id and cita.paciente_id in pacientes_dict:
                if pacientes_dict[cita.paciente_id].odontologo_id != current_user.id:
                    continue
            # Si no tiene paciente, todos pueden verlo (citas genéricas)
        
        citas_por_hora[hora_key] = {
            'id': cita.id,
            'paciente_nombre': paciente_nombre,
            'paciente_apellidos': paciente_apellidos,
            'paciente_telefono': paciente_telefono,
            'motivo': cita.motivo or '',
            'doctor': cita.doctor,
            'estado': cita.estado,
            'edit_url': url_for('calendario.editar_cita', cita_id=cita.id, next=request.full_path)
        }
    
    # Generar franjas de 30 minutos
    franjas = []
    hora_inicio = time(8, 0)
    hora_fin = time(18, 0)
    
    hora_actual = datetime.combine(fecha_seleccionada, hora_inicio)
    hora_fin_dt = datetime.combine(fecha_seleccionada, hora_fin)
    
    while hora_actual <= hora_fin_dt:
        hora_str = hora_actual.strftime('%H:%M')
        franjas.append({
            'hora': hora_str,
            'hora_display': hora_actual.strftime('%I:%M %p'),
            'cita': citas_por_hora.get(hora_str, None)
        })
        hora_actual += timedelta(minutes=30)
    
    # Mini calendario
    mes_actual = fecha_seleccionada.month
    anio_actual = fecha_seleccionada.year
    nombre_mes = NOMBRES_MESES_ESP[mes_actual - 1]
    
    import calendar
    cal = calendar.monthcalendar(anio_actual, mes_actual)
    
    return render_template('vista_diaria.html',
                          fecha_seleccionada=fecha_seleccionada,
                          franjas=franjas,
                          mes_actual=mes_actual,
                          anio_actual=anio_actual,
                          nombre_mes=nombre_mes,
                          calendario_mes=cal,
                          nombres_meses=NOMBRES_MESES_ESP,
                          timedelta=timedelta)