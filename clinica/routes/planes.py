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
    """Permite al usuario cambiar de plan"""
    plan = Plan.query.get_or_404(plan_id)

    if plan.nombre == 'trial':
        flash('El plan Trial se activa automáticamente. Por favor, elige un plan de pago.', 'warning')
        return redirect(url_for('planes.mostrar_planes'))
    
    try:
        # Registrar la solicitud de pago
        solicitud_id, monto_cop = PagoService.registrar_solicitud_manual(
            user_id=current_user.id, 
            plan_id=plan.id, 
            plan_nombre=plan.nombre
        )
        
        # Guardar en sesión para mostrarlo en mi_suscripcion
        session['plan_seleccionado'] = {
            'id': plan.id,
            'nombre': plan.nombre,
            'precio': plan.precio_mensual,
            'solicitud_id': solicitud_id
        }
        
        # Redirigir a mi_suscripcion
        return redirect(url_for('planes.mi_suscripcion'))

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
    import hashlib
    import os
    
    print("=== DEBUG MI SUSCRIPCION ===")
    
    estadisticas = PlanService.obtener_estadisticas_usuario(current_user.id)
    plan_seleccionado = session.get('plan_seleccionado')
    
    if not plan_seleccionado:
        flash('Por favor, selecciona un plan primero.', 'warning')
        return redirect(url_for('planes.mostrar_planes'))
    
    # 🔹 GENERAR FIRMA - VERSIÓN CORREGIDA 🔹
    #monto_centavos = int(plan_seleccionado['precio'] * 100)
    #referencia = f"suscripcion_{current_user.id}_{plan_seleccionado['id']}"
    #integrity_key = os.getenv("WOMPI_INTEGRITY_KEY")
    
    # ¡IMPORTANTE! La cadena debe ser EXACTAMENTE: monto + referencia + llave_integridad
    # SIN espacios, SIN saltos de línea
    #cadena_firma = f"{referencia}{monto_centavos}COP{integrity_key}"
    
    # Generar SHA-256 en hexadecimal
    #firma_integridad = hashlib.sha256(cadena_firma.encode('utf-8')).hexdigest()
    
    # 🔹 DEPURACIÓN - IMPRIMIR TODO 🔹
    #print("="*60)
    print("🔍 VERIFICACIÓN DE FIRMA WOMPI")
    #print(f"💰 Monto en centavos: {monto_centavos}")
    #print(f"📝 Referencia: '{referencia}'")
    #print(f"🔑 Integrity Key: '{integrity_key}'")
    #print(f"📏 Longitud integrity key: {len(integrity_key)}")
    #print(f"🔗 Cadena concatenada: '{cadena_firma}'")
    #print(f"📏 Longitud cadena: {len(cadena_firma)}")
    #print(f"🔐 Firma generada (SHA-256): {firma_integridad}")
    #print(f"🔐 Longitud firma: {len(firma_integridad)} (debe ser 64)")
    #print("="*60)
    
    pagos = Pago.query.join(UsuarioPlan).filter(
        UsuarioPlan.usuario_id == current_user.id
    ).order_by(Pago.fecha_pago.desc()).all()
    
    return render_template(
        'mi_suscripcion.html', 
        estadisticas=estadisticas,
        pagos=pagos,
        now=datetime.utcnow(),
        #wompi_public_key=os.getenv("WOMPI_PUBLIC_KEY"),
        plan_seleccionado=plan_seleccionado,
        #firma_wompi=firma_integridad
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



#@planes_bp.route('/generar-firma-wompi', methods=['POST'])
#@login_required
#def generar_firma_wompi():
    """Genera la firma de integridad para Wompi"""
    try:
        data = request.get_json()
        referencia = data.get('referencia')
        monto = data.get('monto')  # Debe ser el monto en centavos (ej: 2000000 para $20.000)
        
        # 1. Concatenar: monto + referencia + integrity_key
        cadena = f"{monto}{referencia}{os.getenv('WOMPI_INTEGRITY_KEY')}"
        
        # 2. Generar SHA-256
        firma = hashlib.sha256(cadena.encode('utf-8')).hexdigest()
        
        return jsonify({'firma': firma})
        
    except Exception as e:
        print(f"Error generando firma: {e}")
        return jsonify({'error': str(e)}), 500


@planes_bp.route("/pago-exitoso")
@login_required
def pago_exitoso():
    return "Pago recibido. Estamos verificando la transacción."