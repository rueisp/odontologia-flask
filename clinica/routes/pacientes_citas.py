from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Paciente, Cita  # Asegúrate de importar Cita

citas_paciente_bp = Blueprint('citas_paciente', __name__, url_prefix='/pacientes')

@citas_paciente_bp.route('/<int:id>/citas')
@login_required 
def historial_citas(id):
    # 1. Consulta Base: Filtramos por ID y aseguramos que no esté eliminado
    query = Paciente.query.filter_by(id=id, is_deleted=False)
    
    # 2. Control de Acceso: Si no es admin, solo puede ver sus propios pacientes
    if not current_user.is_admin:
        query = query.filter_by(odontologo_id=current_user.id)
        
    paciente = query.first_or_404()
    
    # 3. Obtener Citas: Hacemos una consulta separada para:
    #    a) Filtrar citas eliminadas (is_deleted=False)
    #    b) Ordenar por base de datos (más eficiente que sorted() de Python)
    citas = Cita.query.filter_by(
        paciente_id=paciente.id, 
        is_deleted=False
    ).order_by(
        Cita.fecha.desc(), 
        Cita.hora.desc()
    ).all()
    
    # Usamos un solo template (el que prefieras, he dejado historial_citas.html)
    return render_template('historial_citas.html', paciente=paciente, citas=citas)