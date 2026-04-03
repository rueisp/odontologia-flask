# clinica/decorators/limites.py (versión mejorada)

from functools import wraps
from flask import flash, redirect, url_for, request, jsonify
from flask_login import current_user
from datetime import datetime
import pytz
from clinica.services.plan_service import PlanService
from clinica.models import AuditoriaAcceso, db

def verificar_limite_pacientes(f):
    """
    Decorador para verificar límite diario de pacientes antes de crear uno nuevo.
    Soporta tanto redirecciones normales como respuestas JSON.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'No autenticado'}), 401
            return redirect(url_for('main.login'))
        
        # Verificar límite diario
        verificacion = PlanService.verificar_limite_diario(current_user.id)
        
        if 'error' in verificacion:
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'No tienes un plan activo'}), 403
            flash('No tienes un plan activo. Por favor, contacta al administrador.', 'danger')
            return redirect(url_for('main.dashboard'))
        
        if not verificacion['puede_crear']:
            # Registrar intento de exceder límite
            auditoria = AuditoriaAcceso(
                usuario_id=current_user.id,
                usuario_email=current_user.email,
                tipo_accion='exceder_limite',
                descripcion=f'Intento de crear paciente excediendo límite diario ({verificacion["limite_diario"].contador_pacientes}/{verificacion["limite_diario"].limite_actual})',
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string,
                recurso_tipo='paciente',
                timestamp=datetime.utcnow()
            )
            db.session.add(auditoria)
            db.session.commit()
            
            # Manejar según el tipo de solicitud
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'error': f'Límite diario alcanzado: {verificacion["limite_diario"].contador_pacientes}/{verificacion["limite_diario"].limite_actual} pacientes hoy.'
                }), 429  # 429 Too Many Requests
            
            flash(f'Límite diario alcanzado: {verificacion["limite_diario"].contador_pacientes}/{verificacion["limite_diario"].limite_actual} pacientes hoy. Vuelve mañana o actualiza tu plan.', 'warning')
            return redirect(url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    
    return decorated_function

def verificar_suscripcion_activa(f):
    """
    Decorador para verificar que el usuario tenga una suscripción activa.
    Bloquea acciones si el trial expiró o la suscripción está vencida.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('main.login'))
        
        # 🔥 1. EL PASE MAESTRO: Si eres admin, entras siempre
        if getattr(current_user, 'is_admin', False):
            return f(*args, **kwargs)
        
        # Verificar plan actual
        plan_info = PlanService.obtener_plan_actual_usuario(current_user.id)
        
        if not plan_info:
            flash('No tienes un plan activo. Por favor, suscríbete para continuar.', 'danger')
            return redirect(url_for('planes.mostrar_planes'))
        
        usuario_plan = plan_info['usuario_plan']
        
        # 2. COMPARACIÓN SOLO POR FECHA (Sin horas para evitar errores)
        hoy = datetime.utcnow().date()
        fecha_vencimiento = usuario_plan.fecha_fin.date() if usuario_plan.fecha_fin else None

        if fecha_vencimiento and fecha_vencimiento < hoy:
            if usuario_plan.es_trial:
                flash('Tu periodo de prueba ha expirado.', 'warning')
            else:
                flash('Tu suscripción ha expirado. Por favor, renueva tu plan.', 'warning')
            return redirect(url_for('planes.mostrar_planes'))
        
        return f(*args, **kwargs)
    
    return decorated_function



def verificar_suscripcion_activa(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('main.login'))
        
        # 1. BYPASS ADMIN: Tú entras siempre
        if getattr(current_user, 'is_admin', False):
            return f(*args, **kwargs)
        
        plan_info = PlanService.obtener_plan_actual_usuario(current_user.id)
        if not plan_info:
            flash('No tienes un plan activo.', 'danger')
            return redirect(url_for('planes.mostrar_planes'))
        
        usuario_plan = plan_info['usuario_plan']
        hoy = datetime.utcnow().date()
        
        # 2. COMPARACIÓN JUSTA (Solo fecha)
        if usuario_plan.fecha_fin and usuario_plan.fecha_fin.date() < hoy:
            flash('Tu suscripción ha expirado. Por favor, renueva tu plan.', 'warning')
            return redirect(url_for('planes.mostrar_planes'))
        
        return f(*args, **kwargs)
    return decorated_function

def solo_lectura_si_expirado(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('main.login'))
        
        if getattr(current_user, 'is_admin', False):
            return f(*args, **kwargs)
        
        plan_info = PlanService.obtener_plan_actual_usuario(current_user.id)
        if not plan_info:
            return f(*args, **kwargs)
        
        usuario_plan = plan_info['usuario_plan']
        hoy = datetime.utcnow().date()
        
        if usuario_plan.fecha_fin and usuario_plan.fecha_fin.date() < hoy:
            if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'error': 'Modo solo lectura.'}), 403
                
                flash('Modo solo lectura activado por plan expirado.', 'warning')
                return redirect(request.referrer or url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function