# app/routes/pacientes_evoluciones.py
from flask import Blueprint, redirect, url_for, flash, request, render_template, current_app
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Paciente, Evolucion

from datetime import date, datetime # <--- ¡Asegúrate de importar datetime!
import pytz # <--- ¡IMPORTAR pytz!

evoluciones_bp = Blueprint('evoluciones', __name__, url_prefix='/pacientes')


@evoluciones_bp.route('/editar_evolucion/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_evolucion(id):
    from sqlalchemy.orm import joinedload
    evolucion = Evolucion.query.options(joinedload(Evolucion.paciente)).get_or_404(id)

    if not current_user.is_admin and evolucion.paciente.odontologo_id != current_user.id:
        flash("Acceso denegado. No tienes permiso para editar esta evolución.", "danger")
        return redirect(url_for('pacientes.lista_pacientes'))

    if request.method == 'POST':
        descripcion_form = request.form.get('descripcion', '').strip()

        if descripcion_form:
            evolucion.descripcion = descripcion_form
            try:
                db.session.commit()
                flash('Evolución actualizada correctamente.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar la evolución: {e}', 'danger')
                current_app.logger.error(f"Error al editar evolucion ID {id}: {e}", exc_info=True)
        else:
            flash('La descripción no puede estar vacía.', 'warning')

        return redirect(url_for('pacientes.mostrar_paciente', id=evolucion.paciente_id))

    return render_template('editar_evolucion.html', evolucion=evolucion)


@evoluciones_bp.route('/agregar_evolucion/<int:paciente_id>', methods=['POST'])
@login_required # <--- ¡Añadir login_required! Es una ruta de acción.
def agregar_evolucion(paciente_id):
    descripcion = request.form['descripcion']

    if descripcion and descripcion.strip():
        # --- MODIFICACIONES CLAVE PARA LA ZONA HORARIA ---
        local_timezone = pytz.timezone('America/Bogota') # <--- TU ZONA HORARIA
        now_in_local_tz = datetime.now(local_timezone)
        fecha_local_para_evolucion = now_in_local_tz.date() # Obtener solo la fecha
        # --- FIN MODIFICACIONES ---

        nueva = Evolucion(
            descripcion=descripcion.strip(),
            paciente_id=paciente_id,
            fecha=fecha_local_para_evolucion # <--- ¡ASIGNAR LA FECHA LOCALIZADA!
        )
        db.session.add(nueva)
        try:
            db.session.commit()
            flash('Evolución guardada exitosamente.', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al añadir evolución para paciente {paciente_id}: {e}", exc_info=True)
            flash('Ocurrió un error al guardar la evolución.', 'danger')
    else:
        flash('La descripción de la evolución no puede estar vacía.', 'warning')

    return redirect(url_for('pacientes.mostrar_paciente', id=paciente_id))


@evoluciones_bp.route('/eliminar_evolucion/<int:id>', methods=['POST'])
@login_required
def eliminar_evolucion(id):
    from sqlalchemy.orm import joinedload
    evolucion = Evolucion.query.options(joinedload(Evolucion.paciente)).get_or_404(id)

    if not current_user.is_admin and evolucion.paciente.odontologo_id != current_user.id:
        flash("Acceso denegado. No tienes permiso para eliminar esta evolución.", "danger")
        return redirect(url_for('pacientes.lista_pacientes'))

    paciente_id = evolucion.paciente_id

    try:
        db.session.delete(evolucion)
        db.session.commit()
        flash("Evolución eliminada exitosamente.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar la evolución: {str(e)}", "danger")
        current_app.logger.error(f"Error al eliminar evolucion ID {id}: {e}", exc_info=True)

    return redirect(url_for('pacientes.mostrar_paciente', id=paciente_id))