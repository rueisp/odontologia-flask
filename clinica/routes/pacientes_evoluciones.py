# app/routes/pacientes_evoluciones.py
from flask import Blueprint, redirect, url_for, flash, request, render_template, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import load_only
from ..extensions import db
from ..models import Paciente, Evolucion
from ..campos_activos import load_only_evolucion_activo

from datetime import date, datetime
import pytz

evoluciones_bp = Blueprint('evoluciones', __name__, url_prefix='/pacientes')


@evoluciones_bp.route('/editar_evolucion/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_evolucion(id):
    # Cargar SOLO la evolución con sus campos necesarios
    evolucion = db.session.query(Evolucion).options(
        load_only_evolucion_activo()
    ).get_or_404(id)
    
    # Verificar permisos (necesitamos el paciente para el odontologo_id)
    # Cargamos SOLO el id y odontologo_id del paciente
    paciente = db.session.query(Paciente).options(
        load_only(Paciente.id, Paciente.odontologo_id)
    ).get(evolucion.paciente_id)
    
    if not paciente:
        flash("Paciente no encontrado.", "danger")
        return redirect(url_for('pacientes.lista_pacientes'))

    if not current_user.is_admin and paciente.odontologo_id != current_user.id:
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

    # Para el GET, cargamos también el nombre del paciente para el template
    paciente_nombre = db.session.query(Paciente).options(
        load_only(Paciente.primer_nombre, Paciente.primer_apellido)
    ).get(evolucion.paciente_id)
    
    return render_template('editar_evolucion.html', 
                         evolucion=evolucion,
                         paciente=paciente_nombre)


@evoluciones_bp.route('/agregar_evolucion/<int:paciente_id>', methods=['POST'])
@login_required
def agregar_evolucion(paciente_id):
    descripcion = request.form['descripcion']

    if descripcion and descripcion.strip():
        # Verificar permisos (solo cargamos el odontologo_id)
        paciente = db.session.query(Paciente).options(
            load_only(Paciente.odontologo_id)
        ).get(paciente_id)
        
        if not paciente:
            flash("Paciente no encontrado.", "danger")
            return redirect(url_for('pacientes.lista_pacientes'))
        
        if not current_user.is_admin and paciente.odontologo_id != current_user.id:
            flash("Acceso denegado.", "danger")
            return redirect(url_for('pacientes.lista_pacientes'))

        local_timezone = pytz.timezone('America/Bogota')
        now_in_local_tz = datetime.now(local_timezone)
        fecha_local_para_evolucion = now_in_local_tz.date()

        nueva = Evolucion(
            descripcion=descripcion.strip(),
            paciente_id=paciente_id,
            fecha=fecha_local_para_evolucion
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
    # Cargar SOLO la evolución con campos mínimos
    evolucion = db.session.query(Evolucion).options(
        load_only(Evolucion.id, Evolucion.paciente_id)
    ).get_or_404(id)
    
    # Cargar SOLO el odontologo_id del paciente para verificar permisos
    paciente = db.session.query(Paciente).options(
        load_only(Paciente.odontologo_id)
    ).get(evolucion.paciente_id)
    
    if not paciente:
        flash("Paciente no encontrado.", "danger")
        return redirect(url_for('pacientes.lista_pacientes'))

    if not current_user.is_admin and paciente.odontologo_id != current_user.id:
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


def agregar_evolucion_service(paciente_id, descripcion, usuario):
    """Agrega una evolución a un paciente"""
    try:
        # Verificar que el paciente existe y pertenece al usuario
        from .pacientes_services import obtener_paciente_service
        paciente_data, _, _ = obtener_paciente_service(paciente_id, usuario)
        
        if not paciente_data:
            return {'success': False, 'message': 'Paciente no encontrado'}
        
        # Crear nueva evolución
        nueva_evolucion = Evolucion(
            paciente_id=paciente_id,
            descripcion=descripcion,
            fecha=datetime.utcnow()
        )
        
        db.session.add(nueva_evolucion)
        db.session.commit()
        
        return {'success': True, 'message': 'Evolución agregada correctamente'}
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error al agregar evolución: {e}')
        return {'success': False, 'message': f'Error al agregar evolución: {str(e)}'}