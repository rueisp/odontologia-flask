from flask import Blueprint, render_template, flash, redirect, url_for, abort, request
from flask_login import login_required, current_user
from ..models import SolicitudPago, Usuario, UsuarioPlan, db
from ..services.pago_service import PagoService
from datetime import timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def solo_admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)

@admin_bp.route('/solicitudes')
@login_required
def lista_solicitudes():
    solo_admin()
    # 1. Solicitudes de pago pendientes
    solicitudes = SolicitudPago.query.filter_by(estado='PENDIENTE').order_by(SolicitudPago.fecha_solicitud.desc()).all()
    
    # 2. Lista de todos los usuarios con sus planes actuales
    # Usamos un Join para traer el plan y el usuario en una sola consulta
    usuarios = Usuario.query.all()
    
    return render_template('admin/solicitudes.html', 
                           solicitudes=solicitudes, 
                           usuarios=usuarios)

@admin_bp.route('/aprobar-pago/<int:solicitud_id>', methods=['POST'])
@login_required
def aprobar_pago(solicitud_id):
    solo_admin()
    exito, mensaje = PagoService.verificar_pago(solicitud_id)
    
    if exito:
        flash(f'✅ {mensaje}', 'success')
        # También muestra qué usuario fue activado
        from clinica.models import SolicitudPago
        solicitud = SolicitudPago.query.get(solicitud_id)
        flash(f'Usuario: {solicitud.usuario.username} - Plan: {solicitud.plan_nombre}', 'info')
    else:
        flash(f'❌ {mensaje}', 'danger')
    
    return redirect(url_for('admin.lista_solicitudes'))

@admin_bp.route('/extender-plan/<int:usuario_id>', methods=['POST'])
@login_required
def extender_plan(usuario_id):
    """Suma 30 días al plan actual del usuario"""
    solo_admin()
    u_plan = UsuarioPlan.query.filter_by(usuario_id=usuario_id, estado='activo').first()
    
    if u_plan and u_plan.fecha_fin:
        u_plan.fecha_fin += timedelta(days=30)
        db.session.commit()
        flash(f'Se han añadido 30 días al usuario.', 'success')
    else:
        flash('El usuario no tiene un plan activo para extender.', 'warning')
        
    return redirect(url_for('admin.lista_solicitudes'))

@admin_bp.route('/rechazar/<int:solicitud_id>', methods=['POST'])
@login_required
def rechazar_solicitud(solicitud_id):
    solo_admin()
    solicitud = SolicitudPago.query.get_or_404(solicitud_id)
    db.session.delete(solicitud)
    db.session.commit()
    flash('Solicitud eliminada.', 'info')
    return redirect(url_for('admin.lista_solicitudes'))