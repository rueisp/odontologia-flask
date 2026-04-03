# clinica/routes/pacientes/consultas_ajax.py
from flask import jsonify, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from ...models import Paciente
from . import pacientes_bp

@pacientes_bp.route('/buscar_sugerencias_ajax')
@login_required 
def buscar_sugerencias_ajax():
    termino = request.args.get('q', '').strip().lower()
    if len(termino) < 2: return jsonify([])

    query = Paciente.query.filter(Paciente.is_deleted == False)
    if not current_user.is_admin:
        query = query.filter(Paciente.odontologo_id == current_user.id)

    search = f"%{termino}%"
    resultados = query.filter(or_(
        Paciente.nombres.ilike(search),
        Paciente.apellidos.ilike(search),
        Paciente.documento.ilike(search)
    )).limit(10).all()

    return jsonify([{'id': p.id, 'nombre': f"{p.nombres} {p.apellidos}"} for p in resultados])

@pacientes_bp.route('/obtener_paciente_ajax/<int:id>')
@login_required 
def obtener_paciente_ajax(id): 
    try:
        paciente = Paciente.query.filter_by(id=id, is_deleted=False).first_or_404()
        
        def safe_get(obj, attr):
            return getattr(obj, attr, "") or ""

        # Solo campos que existen en models.py
        return jsonify({
            'id': paciente.id,
            'nombres': safe_get(paciente, 'nombres'),
            'apellidos': safe_get(paciente, 'apellidos'),
            'documento': safe_get(paciente, 'documento'),
            'telefono': safe_get(paciente, 'telefono'),
            'edad': safe_get(paciente, 'edad'),
            'sexo': safe_get(paciente, 'sexo'),
            'email': safe_get(paciente, 'email'),
            'direccion': safe_get(paciente, 'direccion'),
            'barrio': safe_get(paciente, 'barrio')
        })
    except Exception as e:
        current_app.logger.error(f"Error en detalle paciente: {e}")
        return jsonify({'error': str(e)}), 500