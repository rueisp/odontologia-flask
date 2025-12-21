# app/routes/pacientes_citas.py
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Paciente

citas_paciente_bp = Blueprint('citas_paciente', __name__, url_prefix='/pacientes')


@citas_paciente_bp.route('/<int:id>/citas')
@login_required # 1. Proteger la ruta
def historial_citas(id):

    query = Paciente.query.filter_by(id=id)
    
    if not current_user.is_admin:
        query = query.filter_by(odontologo_id=current_user.id)
        
    paciente = query.first_or_404()
    
    citas = sorted(paciente.citas, key=lambda c: (c.fecha, c.hora), reverse=True)
    
    return render_template('historial_citas.html', paciente=paciente, citas=citas)


@citas_paciente_bp.route('/pacientes/<int:id>/citas')
def ver_citas(id):
    paciente = Paciente.query.filter_by(id=id, is_deleted=False).first_or_404()
    citas = Cita.query.filter_by(paciente_id=id, is_deleted=False).all()
    return render_template('ver_citas.html', paciente=paciente, citas=citas)

