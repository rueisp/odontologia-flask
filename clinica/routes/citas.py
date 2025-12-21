from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user # <--- 1. AGREGAR ESTA IMPORTACIÓN
from ..models import db, Cita, Paciente

citas_bp = Blueprint('citas', __name__)

@citas_bp.route('/citas/registrar/<int:paciente_id>', methods=['GET', 'POST'])
@login_required # <--- Es bueno proteger la ruta
def registrar_cita(paciente_id):
    paciente = Paciente.query.get_or_404(paciente_id)

    if request.method == 'POST':
        nueva_cita = Cita(
            paciente_id=paciente.id,
            fecha=request.form['fecha'],
            hora=request.form['hora'],
            motivo=request.form['motivo'],
            observaciones=request.form.get('observaciones'),
            
            # ▼▼▼ 2. AGREGAR ESTAS DOS LÍNEAS ▼▼▼
            odontologo_id=current_user.id,        # Para que sume en el panel
            doctor=current_user.username          # Para llenar el campo de texto obligatorio
            # ▲▲▲ FIN DE LOS CAMBIOS ▲▲▲
        )
        db.session.add(nueva_cita)
        db.session.commit()
        flash('Cita registrada exitosamente.')
        return redirect(url_for('pacientes.ver_historial_citas', id=paciente.id))

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
