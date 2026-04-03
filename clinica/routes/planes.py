# clinica/routes/planes.py

from flask import Blueprint, render_template, flash, redirect, url_for, session
from flask_login import login_required, current_user
import os
from clinica.models import Plan, UsuarioPlan
from ..services.pago_service import PagoService 
from clinica.services.plan_service import PlanService
import hashlib
import json
from flask import jsonify, request

planes_bp = Blueprint('planes', __name__)

# La ruta principal para ver los planes
@planes_bp.route('/planes')  
@login_required
def mostrar_planes():
    """Mostrar página de planes y precios"""
    # Obtener todos los planes activos
    planes = Plan.query.filter_by(activo=True).order_by(Plan.orden).all()
    
    # Obtener estadísticas del usuario actual
    estadisticas = PlanService.obtener_estadisticas_usuario(current_user.id)
    
    # 🔹 NUEVO: Obtener el plan actual del usuario
    plan_actual = None
    plan_info = PlanService.obtener_plan_actual_usuario(current_user.id)
    if plan_info:
        plan_actual = plan_info['plan']
    
    return render_template(
        'planes.html', 
        planes=planes, 
        estadisticas=estadisticas,
        plan_actual=plan_actual  # 🔹 IMPORTANTE: pasar plan_actual al template
    )

# -------------------------------------------------------------
# 1. MODIFICACIÓN: Ruta para Elegir Plan (Inicia el proceso manual)
# -------------------------------------------------------------
  # ← IMPORTANTE: Agrega esto al inicio del archivo

@planes_bp.route('/planes/elegir/<int:plan_id>')  
@login_required
def elegir_plan(plan_id):
    plan = Plan.query.get_or_404(plan_id)

    if plan.nombre == 'trial':
        # 🔥 NUEVA SEGURIDAD:
        if PlanService.ya_uso_trial(current_user.id):
            flash('Ya has utilizado tu periodo de prueba anteriormente. Por favor, elige un plan de pago.', 'warning')
            return redirect(url_for('planes.mostrar_planes'))
        
        # Si no lo ha usado, lo activamos
        exito, mensaje = PlanService.activar_plan(current_user.id, plan.id)

        if exito:
            flash('¡Tu periodo de prueba de 7 días ha comenzado! Bienvenido.', 'success')
            return redirect(url_for('main.dashboard')) # Ahora sí puede entrar
        else:
            flash(mensaje, 'danger')
            return redirect(url_for('planes.mostrar_planes'))

    # --- CASO 2: PLANES DE PAGO (Básico/Pro) ---
    try:
        solicitud_id, monto_cop = PagoService.registrar_solicitud_manual(
            user_id=current_user.id, 
            plan_id=plan.id, 
            plan_nombre=plan.nombre
        )
        
        # Guardar en sesión para la UI
        session['plan_seleccionado'] = {
            'id': plan.id,
            'nombre': plan.nombre,
            'precio': plan.precio_cop, # Usamos el campo COP
            'solicitud_id': solicitud_id
        }
        
        return redirect(url_for('planes.instrucciones_pago', solicitud_id=solicitud_id))

    except Exception as e:
        flash(f'Error al procesar: {str(e)}', 'error')
        return redirect(url_for('planes.mostrar_planes'))

# -------------------------------------------------------------
# 2. NUEVA RUTA: Para mostrar las instrucciones de pago
# -------------------------------------------------------------
@planes_bp.route('/planes/instrucciones/<int:solicitud_id>')  
@login_required
def instrucciones_pago(solicitud_id):
    """Muestra la página con los datos de Bancolombia/Nequi."""
    
    # Recupera los datos de la solicitud de la DB
    solicitud = PagoService.obtener_solicitud_por_id(solicitud_id)
    
    if not solicitud or solicitud.user_id != current_user.id:
        flash('Solicitud de pago inválida.', 'error')
        return redirect(url_for('planes.mostrar_planes'))

    # Pasa el objeto solicitud (con plan_nombre y monto_cop) a la plantilla
    return render_template('instrucciones_pago.html', solicitud=solicitud)


@planes_bp.route('/mi-suscripcion')
@login_required
def mi_suscripcion():
    from datetime import datetime
    from clinica.models import Pago
        
    estadisticas = PlanService.obtener_estadisticas_usuario(current_user.id)
    plan_seleccionado = session.get('plan_seleccionado')
    
    if not plan_seleccionado:
        flash('Por favor, selecciona un plan primero.', 'warning')
        return redirect(url_for('planes.mostrar_planes'))
    
    pagos = Pago.query.join(UsuarioPlan).filter(
        UsuarioPlan.usuario_id == current_user.id
    ).order_by(Pago.fecha_pago.desc()).all()
    
    return render_template(
        'mi_suscripcion.html', 
        estadisticas=estadisticas,
        pagos=pagos,
        now=datetime.utcnow(),
        plan_seleccionado=plan_seleccionado
    )

@planes_bp.route('/cancelar-suscripcion', methods=['POST'])
@login_required
def cancelar_suscripcion():
    """Cancelar la suscripción actual"""
    try:
        # Buscar el plan activo del usuario
        usuario_plan = UsuarioPlan.query.filter_by(
            usuario_id=current_user.id,
            estado='activo'
        ).first()
        
        if usuario_plan:
            usuario_plan.estado = 'cancelado'
            usuario_plan.fecha_cancelacion = datetime.utcnow()
            db.session.commit()
            flash('Tu suscripción ha sido cancelada. Seguirás teniendo acceso hasta el final del período.', 'success')
        else:
            flash('No se encontró una suscripción activa.', 'warning')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error al cancelar: {str(e)}', 'danger')
    
    return redirect(url_for('planes.mi_suscripcion'))


@planes_bp.route('/admin/activar-plan/<int:usuario_id>/<int:plan_id>', methods=['POST'])
@login_required
def admin_activar_plan(usuario_id, plan_id):
    """Ruta interna para activar plan manualmente (solo admin)"""
    if not current_user.is_admin:
        flash('Acceso denegado', 'danger')
        return redirect(url_for('main.dashboard'))
    
    exito, mensaje = PlanService.activar_plan(usuario_id, plan_id)
    
    if exito:
        flash(mensaje, 'success')
    else:
        flash(mensaje, 'danger')
    
    return redirect(url_for('admin.usuarios'))  # Ajusta según tu ruta de admin


@planes_bp.route("/pago-exitoso")
@login_required
def pago_exitoso():
    return "Pago recibido. Estamos verificando la transacción."

