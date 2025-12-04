# clinica/routes/planes.py

from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from clinica.models import Plan, UsuarioPlan
from clinica.services.plan_service import PlanService

planes_bp = Blueprint('planes', __name__)

# CAMBIAR: Quitar '/planes' de las rutas
@planes_bp.route('/planes')  # ← Solo '/' en lugar de '/planes'
@login_required
def mostrar_planes():
    """Mostrar página de planes y precios"""
    planes = Plan.query.filter_by(activo=True).order_by(Plan.orden).all()
    estadisticas = PlanService.obtener_estadisticas_usuario(current_user.id)
    
    return render_template(
        'planes.html', 
        planes=planes, 
        estadisticas=estadisticas
    )

@planes_bp.route('/planes/elegir/<int:plan_id>')  # ← Sin '/planes' al inicio
@login_required
def elegir_plan(plan_id):
    """Permite al usuario cambiar de plan"""
    plan = Plan.query.get_or_404(plan_id)
    flash(f'Redirigiendo a checkout para plan {plan.nombre}...', 'info')
    return redirect(url_for('planes.mostrar_planes'))

@planes_bp.route('/planes/mi-suscripcion')  # ← Sin '/planes' al inicio
@login_required
def mi_suscripcion():
    """Página de gestión de suscripción"""
    plan_info = PlanService.obtener_plan_actual_usuario(current_user.id)
    
    if not plan_info:
        flash('No tienes una suscripción activa.', 'warning')
        return redirect(url_for('planes.mostrar_planes'))
    
    return render_template('mi_suscripcion.html', plan_info=plan_info)