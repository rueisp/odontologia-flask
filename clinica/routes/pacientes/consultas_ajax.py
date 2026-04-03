# clinica/routes/pacientes/consultas_ajax.py

from flask import jsonify, request, url_for, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_, func, case
from datetime import date, datetime

# 1. TRES PUNTOS (...) para subir dos niveles hasta la raíz de clinica
from ...extensions import db
from ...models import Paciente, Cita

# 2. IMPORTAR EL BLUEPRINT: Traemos al único jefe de esta carpeta
from . import pacientes_bp



@pacientes_bp.route('/buscar_sugerencias_ajax')
@login_required 
def buscar_sugerencias_ajax():
    termino = request.args.get('q', '').lower()
    if not termino or len(termino) < 2:
        return jsonify([])

    query_base = Paciente.query.filter(Paciente.is_deleted == False)

    if not current_user.is_admin: # Solo filtrar por odontólogo si no es admin
        query_base = query_base.filter(Paciente.odontologo_id == current_user.id)

    resultados = query_base.filter(
        or_(
            Paciente.nombres.ilike(f"%{termino}%"),
            Paciente.apellidos.ilike(f"%{termino}%"),
            Paciente.documento.ilike(f"%{termino}%")
        )
    ).limit(10).all()

    sugerencias = [{'id': p.id, 'nombre': f"{p.nombres} {p.apellidos}"} for p in resultados]
    return jsonify(sugerencias)

@pacientes_bp.route('/obtener_paciente_ajax/<int:id>')
@login_required 
def obtener_paciente_ajax(id): 
    try:
        # Aseguramos que el paciente pertenece al usuario logueado o es admin
        query_base = Paciente.query.filter_by(id=id, is_deleted=False)
        if not current_user.is_admin:
            query_base = query_base.filter_by(odontologo_id=current_user.id)
        paciente = query_base.first_or_404()

        hoy = date.today()
        ahora_time = datetime.now().time()

        # 1. Última cita del paciente
        ultima_cita_obj = Cita.query.filter(Cita.paciente_id == id, Cita.is_deleted == False)\
            .filter(Cita.fecha < hoy)\
            .order_by(Cita.fecha.desc(), Cita.hora.desc())\
            .first()
        
        ultima_cita_str = "No hay citas anteriores registradas"
        if ultima_cita_obj:
            ultima_cita_str = f"{ultima_cita_obj.fecha.strftime('%d %b, %Y')} - {ultima_cita_obj.motivo or 'Consulta'}"

        # 2. Próxima cita del paciente
        from sqlalchemy import case
        proxima_cita_paciente_obj = Cita.query.filter(Cita.paciente_id == id, Cita.is_deleted == False)\
            .filter(Cita.fecha >= hoy)\
            .filter(case((Cita.fecha == hoy, Cita.hora > ahora_time), else_=(Cita.fecha > hoy)))\
            .order_by(Cita.fecha, Cita.hora)\
            .first()

        proxima_cita_paciente_str = "No tiene próximas citas"
        if proxima_cita_paciente_obj:
            proxima_cita_paciente_str = f"{proxima_cita_paciente_obj.fecha.strftime('%d %b, %Y')} a las {proxima_cita_paciente_obj.hora.strftime('%I:%M %p')} ({proxima_cita_paciente_obj.motivo or 'Consulta'})"
        
        # 3. Motivo de consulta más frecuente
        motivo_frecuente_resultado = db.session.query(Cita.motivo, func.count(Cita.motivo).label('conteo'))\
            .filter(Cita.paciente_id == id, Cita.is_deleted == False)\
            .filter(Cita.motivo != None, Cita.motivo != '')\
            .group_by(Cita.motivo)\
            .order_by(func.count(Cita.motivo).desc())\
            .first()
        
        motivo_frecuente_str = "No especificado"
        if motivo_frecuente_resultado:
            motivo_frecuente_str = motivo_frecuente_resultado.motivo

        # ============================================================
        # SOLO CAMPOS QUE EXISTEN EN models.py
        # ============================================================
        paciente_data = {
            'id': paciente.id,
            'nombre': f"{paciente.nombres} {paciente.apellidos}",
            'nombres': paciente.nombres or '',
            'apellidos': paciente.apellidos or '',
            'sexo': paciente.sexo or '',  # ← campo sexo, no genero
            'edad': paciente.edad if paciente.edad is not None else '',
            'fecha_nacimiento': paciente.fecha_nacimiento.strftime('%d/%m/%Y') if paciente.fecha_nacimiento else '',
            'documento': paciente.documento or '',
            'telefono': paciente.telefono or '',
            'direccion': paciente.direccion or '',
            'barrio': paciente.barrio or '',
            'email': paciente.email or '',
            'alergias': paciente.alergias or '',
            'enfermedad_actual': paciente.enfermedad_actual or '',
            'observaciones': paciente.observaciones or '',
            'dentigrama_url': paciente.dentigrama_canvas or None,
            'imagen_perfil_url': paciente.imagen_perfil_url or None,
            # --- Datos de Citas ---
            'ultima_cita_info': ultima_cita_str,
            'proxima_cita_paciente_info': proxima_cita_paciente_str,
            'motivo_frecuente_info': motivo_frecuente_str,
        }
        return jsonify(paciente_data)
    except Exception as e:
        current_app.logger.error(f"Error en obtener_paciente_ajax para paciente ID {id}: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor al obtener los datos del paciente.'}), 500