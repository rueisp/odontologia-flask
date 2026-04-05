from flask import request, redirect, url_for, flash, render_template, current_app
from flask_login import login_required, current_user
from datetime import datetime
import pytz
from ...models import db, Cita, Paciente
from . import calendario_bp

def is_safe_url(target):
    from urllib.parse import urlparse, urljoin
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def convertir_cita_a_paciente(cita_id, odontologo_id):
    """Convierte una cita con pre-registro a paciente real"""
    cita = Cita.query.filter_by(id=cita_id, odontologo_id=odontologo_id).first()
    
    if not cita or cita.paciente_id is not None:
        return None
    
    if cita.pre_nombres and cita.pre_apellidos:
        nuevo_paciente = Paciente(
            nombres=cita.pre_nombres,
            apellidos=cita.pre_apellidos,
            telefono=cita.pre_telefono or '',
            documento=None,
            odontologo_id=odontologo_id
        )
        db.session.add(nuevo_paciente)
        db.session.flush()
        
        cita.paciente_id = nuevo_paciente.id
        cita.pre_nombres = None
        cita.pre_apellidos = None
        cita.pre_telefono = None
        
        db.session.commit()
        return nuevo_paciente
    
    return None



@calendario_bp.route('/registrar_cita', methods=['GET', 'POST'])
@login_required
def registrar_cita():
    from datetime import datetime
    local_tz = pytz.timezone('America/Bogota')
    fecha_hoy = datetime.now(local_tz).strftime('%d/%m/%Y')
    
    next_url_get = request.args.get('next')
    fecha_preseleccionada_str = request.args.get('fecha') if request.method == 'GET' else None
    hora_preseleccionada_str = request.args.get('hora') if request.method == 'GET' else None
    
    if fecha_preseleccionada_str:
        try:
            fecha_obj = datetime.strptime(fecha_preseleccionada_str, '%Y-%m-%d')
            fecha_preseleccionada_str = fecha_obj.strftime('%d/%m/%Y')
        except ValueError:
            pass
    
    form_values = {
        'paciente_preseleccionado_id': '',
        'paciente_preseleccionado_nombre': '',
        'paciente_nombres_val': '', 'paciente_apellidos_val': '', 'paciente_edad_val': '',
        'paciente_documento_val': '', 'paciente_telefono_val': '',
        'fecha_val': fecha_preseleccionada_str or fecha_hoy,
        'hora_val': hora_preseleccionada_str or '',
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
            
            if not paciente_id_seleccionado and not (nombres_pac_form and apellidos_pac_form and telefono_pac_form):
                flash("Nombres, Apellidos y Teléfono del paciente son obligatorios si no se selecciona un paciente existente.", "error")
                return render_template('registrar_cita.html', form_values=form_values)
            
            if not (fecha_str and hora_str and doctor_form):
                flash("Fecha, Hora y Doctor son campos obligatorios para la cita.", "error")
                return render_template('registrar_cita.html', form_values=form_values)
            
            try:
                fecha_obj = datetime.strptime(fecha_str, "%d/%m/%Y").date()
                hora_obj = datetime.strptime(hora_str, "%H:%M").time()
            except ValueError:
                flash("Formato de fecha u hora inválido.", "error")
                return render_template('registrar_cita.html', form_values=form_values)
            
            cita_existente = Cita.query.filter(
                Cita.fecha == fecha_obj,
                Cita.hora == hora_obj,
                Cita.is_deleted == False,
                Cita.odontologo_id == current_user.id  # 👈 Agregar esta línea
            ).first()

            if cita_existente:
                flash(f"Ya existe una cita para el {fecha_str} a las {hora_str}. Por favor, selecciona otro horario.", "error")
                return render_template('registrar_cita.html', form_values=form_values)

            nueva_cita = Cita(
                fecha=fecha_obj,
                hora=hora_obj,
                doctor=doctor_form,
                motivo=motivo_form or None,
                observaciones=observaciones_form or None,
                odontologo_id=current_user.id,
                paciente_id=None,  # Si es None, cita sin paciente (temporal)
            )
            
            if paciente_id_seleccionado:
                paciente_existente = Paciente.query.filter_by(id=paciente_id_seleccionado, is_deleted=False).first()
                if paciente_existente:
                    nueva_cita.paciente_id = paciente_existente.id
                else:
                    flash("El paciente seleccionado no es válido o ha sido eliminado.", "error")
                    return render_template('registrar_cita.html', form_values=form_values)
            else:
                nueva_cita.pre_nombres = nombres_pac_form
                nueva_cita.pre_apellidos = apellidos_pac_form
                nueva_cita.pre_telefono = telefono_pac_form
            
            db.session.add(nueva_cita)
            db.session.commit()
            flash("Cita registrada correctamente.", "success")
            
            if current_next_url and is_safe_url(current_next_url):
                return redirect(current_next_url)
            return redirect(url_for('calendario.mostrar_calendario', anio=fecha_obj.year, mes=fecha_obj.month))
            
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
            return redirect(url_for('calendario.mostrar_calendario'))
    
    query_pacientes = Paciente.query.filter_by(is_deleted=False)
    if not current_user.is_admin:
        query_pacientes = query_pacientes.filter_by(odontologo_id=current_user.id)
    todos_los_pacientes = query_pacientes.order_by(Paciente.apellidos, Paciente.nombres).all()
    
    next_url_get = request.args.get('next')
    
    form_data_edit = {
        'selected_paciente_id': str(cita_obj.paciente_id) if cita_obj.paciente_id else '',
        'fecha_val': cita_obj.fecha.strftime('%d/%m/%Y'),
        'hora_val': cita_obj.hora.strftime('%H:%M'),
        'doctor_val': cita_obj.doctor,
        'motivo_val': cita_obj.motivo or '',
        'observaciones_val': cita_obj.observaciones or '',
        'next_url': next_url_get,
        # CAMBIADO: usar campos pre_ en lugar de paciente.
        'pre_nombres': cita_obj.pre_nombres or '',
        'pre_apellidos': cita_obj.pre_apellidos or '',
        'pre_telefono': cita_obj.pre_telefono or ''
    }
    
    if request.method == 'POST':
        current_next_url = request.form.get('next') or next_url_get
        paciente_id_form = request.form.get('paciente_id')
        fecha_str = request.form.get('fecha')
        hora_str = request.form.get('hora')
        doctor_form = request.form.get('doctor')
        motivo_form = request.form.get('motivo')
        observaciones_form = request.form.get('observaciones')
        paciente_nombres_form = request.form.get('paciente.nombres', '').strip()
        paciente_apellidos_form = request.form.get('paciente.apellidos', '').strip()
        paciente_telefono_form = request.form.get('paciente.telefono', '').strip()
        
        if not (fecha_str and hora_str and doctor_form):
            flash("Fecha, hora y doctor son campos obligatorios.", "error")
            return render_template('editar_cita.html', cita=cita_obj, pacientes=todos_los_pacientes, form_data=form_data_edit)
        
        try:
            if paciente_id_form and paciente_id_form.strip():
                cita_obj.paciente_id = int(paciente_id_form)
                # CAMBIADO: limpiar pre-registro
                cita_obj.pre_nombres = None
                cita_obj.pre_apellidos = None
                cita_obj.pre_telefono = None
            else:
                cita_obj.paciente_id = None
                # CAMBIADO: guardar en pre-registro
                cita_obj.pre_nombres = paciente_nombres_form or None
                cita_obj.pre_apellidos = paciente_apellidos_form or None
                cita_obj.pre_telefono = paciente_telefono_form or None
            
            cita_obj.fecha = datetime.strptime(fecha_str, "%d/%m/%Y").date()
            cita_obj.hora = datetime.strptime(hora_str, "%H:%M").time()
            cita_obj.doctor = doctor_form
            cita_obj.motivo = motivo_form or None
            cita_obj.observaciones = observaciones_form or None
            
            db.session.commit()
            flash("Cita actualizada correctamente.", "success")
            
        except Exception as e:
            db.session.rollback()
            flash(f"Error al actualizar la cita: {e}", "error")
            return render_template('editar_cita.html', cita=cita_obj, pacientes=todos_los_pacientes, form_data=form_data_edit)
        
        if current_next_url and is_safe_url(current_next_url):
            return redirect(current_next_url)
        return redirect(url_for('calendario.mostrar_calendario', anio=cita_obj.fecha.year, mes=cita_obj.fecha.month))
    
    return render_template('editar_cita.html', cita=cita_obj, pacientes=todos_los_pacientes, form_data=form_data_edit)


@calendario_bp.route('/eliminar_cita/<int:cita_id>', methods=['POST'])
@login_required
def eliminar_cita(cita_id):
    from ...models import AuditLog
    
    cita = Cita.query.get_or_404(cita_id)
    
    if not current_user.is_admin and cita.paciente_id:
        paciente = Paciente.query.get(cita.paciente_id)
        if paciente and paciente.odontologo_id != current_user.id:
            flash("Acceso denegado.", "danger")
            return redirect(url_for('calendario.mostrar_calendario'))
    
    next_url = request.form.get('next')
    
    try:
        cita.is_deleted = True
        cita.deleted_at = datetime.now(pytz.timezone('America/Bogota'))
        db.session.commit()
        flash("Cita eliminada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar la cita: {e}", "error")
    
    if next_url and is_safe_url(next_url):
        return redirect(next_url)
    return redirect(url_for('calendario.mostrar_calendario'))


@calendario_bp.route('/historial_citas_paciente/<int:paciente_id>', methods=['GET'])
@login_required
def historial_citas_paciente(paciente_id):
    paciente = Paciente.query.filter_by(id=paciente_id, is_deleted=False).first_or_404()
    if not current_user.is_admin and paciente.odontologo_id != current_user.id:
        flash("Acceso denegado.", "danger")
        return redirect(url_for('pacientes.lista_pacientes'))
    
    citas_query = Cita.query.filter(
        Cita.paciente_id == paciente_id,
        Cita.is_deleted == False
    ).order_by(Cita.fecha.desc(), Cita.hora.desc())
    
    citas_del_paciente = citas_query.all()
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
                           citas=citas_procesadas)


@calendario_bp.route('/cita/actualizar_estado/<int:cita_id>', methods=['POST'])
@login_required
def actualizar_estado_cita(cita_id):
    cita = Cita.query.get(cita_id)
    if not cita:
        return jsonify({'success': False, 'message': 'Cita no encontrada.'}), 404
    
    if not current_user.is_admin and cita.paciente_id:
        paciente = Paciente.query.get(cita.paciente_id)
        if paciente and paciente.odontologo_id != current_user.id:
            return jsonify({'success': False, 'message': 'No tienes permiso.'}), 403
    
    data = request.get_json()
    nuevo_estado = data.get('estado')
    estados_validos = ['pendiente', 'completada', 'cancelada', 'confirmada', 'reprogramada', 'no_asistio']
    
    if nuevo_estado not in estados_validos:
        return jsonify({'success': False, 'message': 'Estado no válido.'}), 400
    
    try:
        cita.estado = nuevo_estado
        db.session.commit()
        return jsonify({'success': True, 'message': 'Estado actualizado.', 'nuevo_estado': nuevo_estado})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
