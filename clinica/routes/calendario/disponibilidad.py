from flask import request, jsonify
from flask_login import login_required
from datetime import datetime
from ...models import Cita
from . import calendario_bp


@calendario_bp.route('/verificar_disponibilidad', methods=['GET'])
@login_required
def verificar_disponibilidad():
    """Verifica si un horario está disponible para agendar una cita"""
    fecha_str = request.args.get('fecha')
    hora_str = request.args.get('hora')
    
    if not fecha_str or not hora_str:
        return jsonify({'disponible': False, 'error': 'Faltan parámetros'})
    
    try:
        fecha_obj = datetime.strptime(fecha_str, '%d/%m/%Y').date()
        hora_obj = datetime.strptime(hora_str, '%H:%M').time()
        
        cita_existente = Cita.query.filter(
            Cita.fecha == fecha_obj,
            Cita.hora == hora_obj,
            Cita.is_deleted == False
        ).first()
        
        return jsonify({'disponible': cita_existente is None})
    except Exception as e:
        return jsonify({'disponible': False, 'error': str(e)})