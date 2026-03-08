# clinica/routes/papelera.py
import os
import cloudinary.uploader
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app
)
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from ..utils import extract_public_id_from_url
from ..extensions import db
from ..models import Paciente, Cita, Evolucion, AuditLog  # ← ELIMINADOS Procedimiento y Factura
try:
    from . import utils
except ImportError:
    from .. import utils

papelera_bp = Blueprint('papelera', __name__, template_folder='../templates')


@papelera_bp.route("/")
@login_required
def ver_papelera():
    """Muestra los elementos que han sido 'soft-deleted', filtrando por usuario."""
    try:
        if current_user.is_admin:
            # El admin ve todo, sin filtros de usuario
            pacientes_eliminados = Paciente.query.filter_by(is_deleted=True)\
                                                .order_by(Paciente.deleted_at.desc()).limit(20).all()
            
            citas_eliminadas = Cita.query.filter_by(is_deleted=True)\
                                        .options(joinedload(Cita.paciente))\
                                        .order_by(Cita.deleted_at.desc()).limit(20).all()
        else:
            # --- FILTRO PARA USUARIO NORMAL (DOCTOR) ---
            
            # 1. Filtro para pacientes
            pacientes_eliminados = Paciente.query.filter_by(
                is_deleted=True, 
                odontologo_id=current_user.id
            ).order_by(Paciente.deleted_at.desc()).limit(20).all()

            # 2. Filtro para citas
            citas_eliminadas = Cita.query.join(Paciente).filter(
                Cita.is_deleted == True,
                Paciente.odontologo_id == current_user.id
            ).options(joinedload(Cita.paciente))\
                .order_by(Cita.deleted_at.desc()).limit(20).all()

    except Exception as e:
        current_app.logger.error(f"Error al cargar la papelera para el usuario {current_user.id}: {e}", exc_info=True)
        flash("Hubo un error al cargar los elementos de la papelera.", "danger")
        pacientes_eliminados = []
        citas_eliminadas = []

    return render_template(
        "papelera.html", 
        pacientes_eliminados=pacientes_eliminados, 
        citas_eliminadas=citas_eliminadas
    )

@papelera_bp.route('/restaurar', methods=['POST'])
@login_required
def restaurar_elemento():
    """Restaura un elemento desde la papelera (soft-delete inverso)."""
    target_model_str = request.form.get('target_model')
    target_id = request.form.get('target_id', type=int)
    action_source = request.referrer

    if not target_model_str or not target_id:
        flash("Información inválida para la restauración.", "danger")
        return redirect(action_source or url_for('papelera.ver_papelera'))

    model_map = {"Paciente": Paciente, "Cita": Cita, "Evolucion": Evolucion}
    model_class = model_map.get(target_model_str)

    if not model_class:
        flash(f"No se puede restaurar el tipo de objeto: {target_model_str}", "danger")
        return redirect(action_source or url_for('papelera.ver_papelera'))

    query = model_class.query.filter_by(id=target_id, is_deleted=True)
    
    # Añadimos el filtro de seguridad si el usuario no es admin
    if not current_user.is_admin:
        # Asumiendo que todos los modelos relevantes tienen 'odontologo_id'
        if hasattr(model_class, 'odontologo_id'):
            query = query.filter_by(odontologo_id=current_user.id)

    objeto_a_restaurar = query.first()

    if not objeto_a_restaurar:
        flash("El elemento no se encontró en la papelera o ya fue restaurado.", "warning")
        return redirect(action_source or url_for('papelera.ver_papelera'))

    try:
        objeto_a_restaurar.is_deleted = False
        objeto_a_restaurar.deleted_at = None
        
        # Crear log de auditoría
        log_description = f"{target_model_str} (ID: {target_id}) restaurado desde la papelera."
        audit_entry = AuditLog(
            action_type=f"RESTAURAR_{target_model_str.upper()}",
            description=log_description,
            target_model=target_model_str,
            target_id=target_id,
            user_id=current_user.id,
            user_username=current_user.username
        )
        db.session.add(audit_entry)
        db.session.commit()
        flash(f"{target_model_str} restaurado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al restaurar {target_model_str} ID {target_id}: {e}", exc_info=True)
        flash(f"Error al restaurar el elemento: {str(e)}", "danger")
        
    return redirect(action_source or url_for('papelera.ver_papelera'))

@papelera_bp.route('/eliminar-permanente', methods=['POST'])
@login_required
def eliminar_permanentemente():
    """Elimina un elemento de forma permanente de la DB y sus archivos asociados."""
    target_model_str = request.form.get('target_model')
    target_id = request.form.get('target_id', type=int)
    action_source = request.referrer

    if not target_model_str or not target_id:
        flash("Información inválida para la eliminación permanente.", "danger")
        return redirect(action_source or url_for('papelera.ver_papelera'))

    model_map = {"Paciente": Paciente, "Cita": Cita, "Evolucion": Evolucion}
    model_class = model_map.get(target_model_str)

    if not model_class:
        flash(f"No se puede eliminar el tipo de objeto: {target_model_str}", "danger")
        return redirect(action_source or url_for('papelera.ver_papelera'))
    
    query = model_class.query.filter_by(id=target_id, is_deleted=True)

    if not current_user.is_admin:
        if hasattr(model_class, 'odontologo_id'):
            query = query.filter_by(odontologo_id=current_user.id)

    objeto_a_eliminar = query.first()
    if not objeto_a_eliminar:
        flash("El elemento no se encontró en la papelera.", "warning")
        return redirect(action_source or url_for('papelera.ver_papelera'))

    try:
        log_descripcion_base = f"{target_model_str} (ID: {target_id})"
        
        if target_model_str == "Paciente":
            # --- DEPURACIÓN ---
            print("=============================================")
            print(f"INICIANDO BORRADO PERMANENTE DEL PACIENTE ID: {objeto_a_eliminar.id}")
            print(f"URL del Dentigrama: {objeto_a_eliminar.dentigrama_canvas}")
            print("---------------------------------------------")

            # Eliminar imágenes de Cloudinary
            if objeto_a_eliminar.dentigrama_canvas:
                public_id = extract_public_id_from_url(objeto_a_eliminar.dentigrama_canvas)
                if public_id:
                    try:
                        cloudinary.uploader.destroy(public_id)
                        current_app.logger.info(f"Éxito al eliminar de Cloudinary: {public_id}")
                    except Exception as e_cloud:
                        current_app.logger.error(f"Fallo al eliminar de Cloudinary {public_id}: {e_cloud}")

            # Eliminar TODAS las EVOLUCIONES asociadas al paciente
            Evolucion.query.filter_by(paciente_id=target_id).delete(synchronize_session=False)
            current_app.logger.info(f"Eliminadas evoluciones del paciente {target_id}.")

            # Eliminar TODAS las CITAS asociadas al paciente
            Cita.query.filter_by(paciente_id=target_id).delete(synchronize_session=False)
            current_app.logger.info(f"Eliminadas citas del paciente {target_id}.")

        elif target_model_str == "Cita":
            # Para citas, no hay acciones adicionales
            pass
            
        elif target_model_str == "Evolucion":
            # Para evoluciones, no hay acciones adicionales
            pass

        # Eliminar el objeto de la DB (Hard Delete)
        db.session.delete(objeto_a_eliminar)

        # Crear log de auditoría
        audit_entry = AuditLog(
            action_type=f"DELETE_PERMANENT_{target_model_str.upper()}",
            description=f"{log_descripcion_base} eliminado permanentemente.",
            target_model=target_model_str,
            target_id=target_id,
            user_id=current_user.id,
            user_username=current_user.username
        )
        db.session.add(audit_entry)

        db.session.commit()
        flash(f"{target_model_str} ha sido eliminado permanentemente.", "success")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error en eliminación permanente de {target_model_str} ID {target_id}: {e}", exc_info=True)
        flash(f"Error al eliminar permanentemente el elemento: {str(e)}", "danger")
        
    return redirect(action_source or url_for('papelera.ver_papelera'))