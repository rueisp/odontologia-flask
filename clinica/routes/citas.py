from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models import db, Cita, Paciente
from datetime import datetime  # Importar para manejar fechas

citas_bp = Blueprint('citas', __name__)

@citas_bp.route('/citas/registrar/<int:paciente_id>', methods=['GET', 'POST'])
@login_required
def registrar_cita(paciente_id):
    paciente = Paciente.query.get_or_404(paciente_id)

    if request.method == 'POST':
        # Obtener los datos del formulario
        fecha_str = request.form['fecha']
        hora_str = request.form['hora']
        doctor_nombre = request.form.get('doctor', '')  # Obtener el doctor del formulario
        
        # Si no viene doctor, usar el current_user
        if not doctor_nombre:
            doctor_nombre = current_user.username
        
        # Convertir fecha y hora
        try:
            # Intentar formato DD/MM/YYYY (como viene del flatpickr)
            fecha = datetime.strptime(fecha_str, '%d/%m/%Y').date()
            print(f"Fecha convertida: {fecha}")
        except:
            try:
                # Intentar formato YYYY-MM-DD
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                print(f"Fecha convertida: {fecha}")
            except Exception as e:
                flash(f'Formato de fecha inválido: {fecha_str}', 'danger')
                return redirect(url_for('citas.registrar_cita', paciente_id=paciente_id))
        
        try:
            # Convertir hora (formato HH:MM)
            hora = datetime.strptime(hora_str, '%H:%M').time()
            print(f"Hora convertida: {hora}")
        except Exception as e:
            flash(f'Formato de hora inválido: {hora_str}', 'danger')
            return redirect(url_for('citas.registrar_cita', paciente_id=paciente_id))
        
        # ✅ VERIFICAR SI EL HORARIO YA ESTÁ OCUPADO PARA ESE DOCTOR
        cita_existente = Cita.query.filter(
            Cita.fecha == fecha,
            Cita.hora == hora,
            Cita.doctor == doctor_nombre,  # Usar el nombre del doctor
            Cita.is_deleted == False
        ).first()
        
        print(f"Buscando cita existente para fecha={fecha}, hora={hora}, doctor={doctor_nombre}")
        print(f"Cita encontrada: {cita_existente}")
        
        if cita_existente:
            flash(f'Este horario ya está ocupado para el doctor {doctor_nombre}. Por favor, selecciona otro horario.', 'danger')
            return redirect(url_for('citas.registrar_cita', paciente_id=paciente_id))
        
        if paciente_id:
            # Caso 1: Paciente ya registrado
            nueva_cita = Cita(
                fecha=fecha_obj,
                hora=hora_obj,
                doctor=doctor_form,
                motivo=motivo_form or None,
                observaciones=observaciones_form or None,
                odontologo_id=current_user.id,
                paciente_id=paciente_id
            )
        else:
            # Caso 2: Paciente nuevo - solo nombre, apellido y teléfono
            nueva_cita = Cita(
                fecha=fecha_obj,
                hora=hora_obj,
                doctor=doctor_form,
                motivo=motivo_form or None,
                observaciones=observaciones_form or None,
                odontologo_id=current_user.id,
                paciente_id=None,
                pre_nombres=paciente_nombres,
                pre_apellidos=paciente_apellidos,
                pre_telefono=paciente_telefono
            )
        
        db.session.add(nueva_cita)
        db.session.commit()
        
        flash('Cita registrada exitosamente.', 'success')
        return redirect(url_for('pacientes.ver_historial_citas', id=paciente.id))

    # GET - Mostrar formulario
    return render_template('registrar_cita.html', paciente=paciente)


# ... (El resto del archivo editar_cita y eliminar_cita déjalo igual)
@citas_bp.route('/citas/editar/<int:id>', methods=['GET', 'POST'])
def editar_cita(id):
    cita = Cita.query.get_or_404(id)

    if request.method == 'POST':
        cita.fecha = request.form['fecha']
        cita.hora = request.form['hora']
        cita.motivo = request.form['motivo']
        cita.observaciones = request.form.get('observaciones')
        db.session.commit()
        flash('Cita actualizada exitosamente.')
        return redirect(url_for('pacientes.ver_historial_citas', id=cita.paciente_id))

    return render_template('editar_cita.html', cita=cita)

@citas_bp.route('/citas/eliminar/<int:id>', methods=['POST'])
def eliminar_cita(id):
    cita = Cita.query.get_or_404(id)
    paciente_id = cita.paciente_id
    db.session.delete(cita)
    db.session.commit()
    flash('Cita eliminada correctamente.')
    return redirect(url_for('pacientes.ver_historial_citas', id=paciente_id))
