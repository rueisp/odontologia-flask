"""
API endpoints for autocomplete functionality.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required
from sqlalchemy import or_
from ..models import CUPSCode, CIE10
from ..extensions import db

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/cups/search', methods=['GET'])
@login_required
def search_cups():
    """
    Busca códigos CUPS por término de búsqueda.
    Query params: q (término de búsqueda)
    Returns: JSON con lista de códigos CUPS
    """
    query_term = request.args.get('q', '').strip()
    
    if not query_term or len(query_term) < 2:
        return jsonify([])
    
    # Buscar en código o descripción
    results = CUPSCode.query.filter(
        or_(
            CUPSCode.code.ilike(f'%{query_term}%'),
            CUPSCode.description.ilike(f'%{query_term}%')
        )
    ).limit(20).all()
    
    # Formatear resultados
    cups_list = [
        {
            'code': cup.code,
            'description': cup.description,
            'label': f'{cup.code} - {cup.description}'
        }
        for cup in results
    ]
    
    return jsonify(cups_list)


@api_bp.route('/cie10/search', methods=['GET'])
@login_required
def search_cie10():
    """
    Busca códigos CIE-10 por término de búsqueda.
    Query params: q (término de búsqueda)
    Returns: JSON con lista de códigos CIE-10
    """
    query_term = request.args.get('q', '').strip()
    
    if not query_term or len(query_term) < 2:
        return jsonify([])
    
    # Buscar en código o descripción
    results = CIE10.query.filter(
        or_(
            CIE10.codigo.ilike(f'%{query_term}%'),
            CIE10.descripcion.ilike(f'%{query_term}%')
        )
    ).limit(20).all()
    
    # Formatear resultados
    cie10_list = [
        {
            'codigo': cie.codigo,
            'descripcion': cie.descripcion,
            'categoria': cie.categoria,
            'label': f'{cie.codigo} - {cie.descripcion}'
        }
        for cie in results
    ]
    
    return jsonify(cie10_list)
