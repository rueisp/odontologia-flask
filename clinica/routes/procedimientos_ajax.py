from flask import Blueprint, jsonify, request
from flask_login import login_required
from sqlalchemy import or_
from ..models import CUPSCode, CIE10 # Asegúrate de que importas tus modelos correctamente

# Creamos un Blueprint separado para no mezclarlo con pacientes
procedimientos_ajax_bp = Blueprint('procedimientos_ajax', __name__, url_prefix='/api/procedimientos')

@procedimientos_ajax_bp.route('/buscar_cups')
@login_required
def buscar_cups():
    """Busca códigos CUPS por código o descripción"""
    termino = request.args.get('q', '').lower()
    if not termino or len(termino) < 2:
        return jsonify([])

    # Buscamos coincidencias en código O descripción
    resultados = CUPSCode.query.filter(
        or_(
            CUPSCode.code.ilike(f"%{termino}%"),
            CUPSCode.description.ilike(f"%{termino}%")
        )
    ).limit(10).all()

    # Formateamos para que el JS lo entienda fácil
    sugerencias = [{
        'val': r.code, 
        'label': f"{r.code} - {r.description}"
    } for r in resultados]
    
    return jsonify(sugerencias)

@procedimientos_ajax_bp.route('/buscar_cie10')
@login_required
def buscar_cie10():
    """Busca diagnósticos CIE10 por código o descripción"""
    termino = request.args.get('q', '').lower()
    if not termino or len(termino) < 2:
        return jsonify([])

    resultados = CIE10.query.filter(
        or_(
            CIE10.codigo.ilike(f"%{termino}%"),
            CIE10.descripcion.ilike(f"%{termino}%")
        )
    ).limit(10).all()

    sugerencias = [{
        'val': r.codigo, 
        'label': f"{r.codigo} - {r.descripcion}"
    } for r in resultados]
    
    return jsonify(sugerencias)