# clinica/routes/planes.py

from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user

# DEBES TENER ESTA LÍNEA (O SIMILAR) PARA IMPORTAR TUS MODELOS:
from clinica.models import Plan, UsuarioPlan # <-- ¡Revisa esta línea!

# La importación que resolvimos hace un momento
from ..services.pago_service import PagoService 

from clinica.services.plan_service import PlanService

planes_bp = Blueprint('planes', __name__)

# La ruta principal para ver los planes
@planes_bp.route('/planes')  
@login_required
def mostrar_planes():
    """Mostrar página de planes y precios"""
    # ... (código existente) ...
    planes = Plan.query.filter_by(activo=True).order_by(Plan.orden).all()
    estadisticas = PlanService.obtener_estadisticas_usuario(current_user.id)
    
    return render_template(
        'planes.html', 
        planes=planes, 
        estadisticas=estadisticas
    )

# -------------------------------------------------------------
# 1. MODIFICACIÓN: Ruta para Elegir Plan (Inicia el proceso manual)
# -------------------------------------------------------------
@planes_bp.route('/planes/elegir/<int:plan_id>')  
@login_required
def elegir_plan(plan_id):
    """Permite al usuario cambiar de plan e inicia la solicitud de pago manual."""
    plan = Plan.query.get_or_404(plan_id)

    if plan.nombre == 'trial':
        flash('El plan Trial se activa automáticamente. Por favor, elige un plan de pago.', 'warning')
        return redirect(url_for('planes.mostrar_planes'))
    
    # **ESTO ES LO NUEVO:** Registrar la solicitud de pago en la base de datos
    # Asume que PagoService es un módulo que creaste para interactuar con la DB
    try:
        solicitud_id, monto_cop = PagoService.registrar_solicitud_manual(
            user_id=current_user.id, 
            plan_id=plan.id, 
            plan_nombre=plan.nombre
            # Asume que PagoService sabe obtener el plan.precio_cop
        )
        
        # Redirigir a la nueva página de instrucciones
        return redirect(url_for('planes.instrucciones_pago', solicitud_id=solicitud_id))

    except Exception as e:
        # En caso de error (ej. conexión a la DB falló al registrar la solicitud)
        flash(f'No se pudo generar la solicitud de pago. Intenta más tarde. Error: {str(e)}', 'error')
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
    
    if not estadisticas:
        flash('No tienes una suscripción activa.', 'warning')
        return redirect(url_for('planes.mostrar_planes'))
    
    # Obtener pagos del usuario
    pagos = Pago.query.join(UsuarioPlan).filter(
        UsuarioPlan.usuario_id == current_user.id
    ).order_by(Pago.fecha_pago.desc()).all()
    
    return render_template(
        'mi_suscripcion.html', 
        estadisticas=estadisticas,
        pagos=pagos,
        now=datetime.utcnow()
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