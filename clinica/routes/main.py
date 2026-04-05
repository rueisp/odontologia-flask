# ▼▼▼ IMPORTACIONES COMPLETAS ▼▼▼
from flask import Blueprint, render_template, current_app, flash, request, redirect, url_for
from flask_login import login_required, current_user, login_user, logout_user
from datetime import datetime, timedelta, time
import pytz
# Importamos los modelos necesarios SOLAMENTE
from clinica.models import Cita, Paciente, Usuario, Plan, UsuarioPlan, SolicitudPago
from clinica import db
from sqlalchemy import func, extract
import locale
from clinica.decorators.limites import verificar_suscripcion_activa
from sqlalchemy.orm import load_only
from clinica.extensions import cache
from sqlalchemy import text 



# Intentar configurar locale en español
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'spanish')
    except:
        pass  # Si no funciona, mantiene el locale por defecto


main_bp = Blueprint('main', __name__)


@main_bp.route("/")
def inicio():
    """Landing page pública"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    from clinica.models import Plan
    planes = Plan.query.filter_by(activo=True).order_by(Plan.orden).all()
    return render_template('landing.html', planes=planes)


@main_bp.route("/dashboard")
@login_required
@verificar_suscripcion_activa
@cache.cached(timeout=60, key_prefix=lambda: f'dashboard_{current_user.get_id()}')
def dashboard():
    # 1. Fecha y Hora Local
    local_timezone = pytz.timezone('America/Bogota')
    now_in_local_tz = datetime.now(local_timezone)

    # Diccionario manual para días y meses en español
    dias_semana = {
        0: 'lunes', 1: 'martes', 2: 'miércoles', 3: 'jueves',
        4: 'viernes', 5: 'sábado', 6: 'domingo'
    }
    meses = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
        5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
        9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
    }

    fecha_actual_formateada = f"{dias_semana[now_in_local_tz.weekday()]}, {now_in_local_tz.day} de {meses[now_in_local_tz.month]} de {now_in_local_tz.year}"
    # 2. CITAS DE HOY
    hoy_date = now_in_local_tz.date()
    LIMITE_CITAS_VISIBLES = 5  # Cambia este valor según prefieras
    # ✅ CAMBIA A:
    citas_hoy = Cita.query.options(
        load_only(Cita.id, Cita.paciente_id, Cita.hora, Cita.motivo, Cita.doctor, Cita.estado)
    ).filter(
        Cita.fecha == hoy_date,
        Cita.is_deleted == False,
        Cita.odontologo_id == current_user.id
    ).order_by(Cita.hora).all()
    
    # Procesar citas para el template
    citas_procesadas = []
    paciente_ids = list(set([c.paciente_id for c in citas_hoy if c.paciente_id]))
    
    # Cargar datos de pacientes
    pacientes_dict = {}
    if paciente_ids:
        pacientes = Paciente.query.options(

        ).filter(Paciente.id.in_(paciente_ids)).all()
        for p in pacientes:
            pacientes_dict[p.id] = p
    
    for cita in citas_hoy:

        if cita.paciente_id:
            paciente = pacientes_dict.get(cita.paciente_id)
            if paciente:
                nombre_completo = f"{paciente.nombres} {paciente.apellidos}".strip()
                telefono = paciente.telefono or ""
            else:
                nombre_completo = f"{cita.pre_nombres or ''} {cita.pre_apellidos or ''}".strip()
                telefono = cita.pre_telefono or ""
        else:
            nombre_completo = f"{cita.pre_nombres or ''} {cita.pre_apellidos or ''}".strip()
            telefono = cita.pre_telefono or ""

        if not nombre_completo or nombre_completo == " ":
            nombre_completo = "Paciente sin registrar"
        
        citas_procesadas.append({
            'id': cita.id,
            'paciente_nombre_completo': nombre_completo,
            'hora_formateada': cita.hora.strftime('%I:%M %p'),
            'motivo': cita.motivo or 'Consulta',
            'doctor': cita.doctor,
            'estado': cita.estado,
            'telefono': telefono
        })
    
    # =====================================================
    # NUEVO: 2.5 CITAS DE MAÑANA
    # =====================================================
    manana_date = hoy_date + timedelta(days=1)
    fecha_manana_formateada = manana_date.strftime('%A, %d de %B de %Y')
    

    # ✅ CAMBIA A:
    citas_manana = Cita.query.options(
        load_only(Cita.id, Cita.paciente_id, Cita.hora, Cita.motivo, Cita.doctor, Cita.estado)
    ).filter(
        Cita.fecha == manana_date,
        Cita.is_deleted == False,
        Cita.odontologo_id == current_user.id
    ).order_by(Cita.hora).all()


    # 👇 PEGA LOS PRINTS AQUÍ 👇
    print("=== DEBUG CITAS MAÑANA ===")
    print(f"Fecha mañana: {manana_date}")
    print(f"Citas encontradas: {len(citas_manana)}")
    for c in citas_manana:
        print(f"Cita ID: {c.id}, Paciente ID: {c.paciente_id}, pre_nombres: {c.pre_nombres}, pre_apellidos: {c.pre_apellidos}")

    
    # Procesar citas de mañana
    citas_manana_procesadas = []
    paciente_ids_manana = list(set([c.paciente_id for c in citas_manana if c.paciente_id]))
    
    # Cargar datos de pacientes para mañana (reutilizar pacientes_dict o cargar nuevos)
    if paciente_ids_manana:
        pacientes_manana = Paciente.query.options(
        ).filter(Paciente.id.in_(paciente_ids_manana)).all()
        for p in pacientes_manana:
            if p.id not in pacientes_dict:
                pacientes_dict[p.id] = p
    
    for cita in citas_manana:
        # Para TODAS las citas (hoy y mañana), usa esta lógica:
        if cita.paciente_id:
            paciente = pacientes_dict.get(cita.paciente_id)
            if paciente:
                nombre_completo = f"{paciente.nombres} {paciente.apellidos}".strip()
                telefono = paciente.telefono or ""
            else:
                nombre_completo = f"{cita.pre_nombres or ''} {cita.pre_apellidos or ''}".strip()
                telefono = cita.pre_telefono or ""
        else:
            nombre_completo = f"{cita.pre_nombres or ''} {cita.pre_apellidos or ''}".strip()
            telefono = cita.pre_telefono or ""

        if not nombre_completo or nombre_completo == " ":
            nombre_completo = "Paciente sin registrar"
        
        citas_manana_procesadas.append({
            'id': cita.id,
            'paciente_nombre_completo': nombre_completo,
            'hora_formateada': cita.hora.strftime('%I:%M %p'),
            'motivo': cita.motivo or 'Consulta',
            'doctor': cita.doctor,
            'estado': cita.estado,
            'telefono': telefono
        })
    
    # 3. CONTADOR SEMANAL
    try:
        inicio_semana = hoy_date - timedelta(days=hoy_date.weekday())
        fin_semana = inicio_semana + timedelta(days=6)
        
        total_citas_semana = Cita.query.filter(
            Cita.fecha >= inicio_semana,
            Cita.fecha <= fin_semana,
            Cita.is_deleted == False,
            Cita.odontologo_id == current_user.id
        ).count()
    except Exception as e:
        current_app.logger.error(f"Error calculando citas semanales: {e}")
        total_citas_semana = 0
    
    # 4. PRÓXIMA CITA
    # ✅ CAMBIA A:
    proxima_cita = Cita.query.options(
        load_only(Cita.id, Cita.fecha, Cita.hora, Cita.paciente_id)
    ).filter(
        Cita.fecha >= hoy_date,
        Cita.is_deleted == False,
        Cita.odontologo_id == current_user.id
    ).order_by(Cita.fecha, Cita.hora).first()
    
    proxima_cita_info = None
    if proxima_cita:
        if proxima_cita.paciente_id and proxima_cita.paciente_id in pacientes_dict:
            paciente = pacientes_dict[proxima_cita.paciente_id]
            paciente_nombre = f"{paciente.nombres} {paciente.apellidos}".strip()
        else:
            # ✅ Usar pre_nombres y pre_apellidos en lugar de paciente.nombres
            paciente_nombre = f"{proxima_cita.pre_nombres or ''} {proxima_cita.pre_apellidos or ''}".strip()
        
        if not paciente_nombre:
            paciente_nombre = "Paciente sin registrar"
        
        proxima_cita_info = {
            'fecha_formateada': proxima_cita.fecha.strftime('%d/%m/%Y'),
            'hora': proxima_cita.hora.strftime('%H:%M'),
            'paciente_nombre': paciente_nombre
        }
    
    # 5. Estadísticas de plan y límites
    from clinica.services.plan_service import PlanService
    estadisticas_plan = PlanService.obtener_estadisticas_usuario(current_user.id)

    citas_hoy_count = len(citas_procesadas)

    estadisticas = {
        'citas_hoy': citas_hoy_count
    }

    return render_template(
        "index.html",
        citas_del_dia=citas_procesadas,
        citas_manana=citas_manana_procesadas,  # NUEVO
        fecha_manana_formateada=fecha_manana_formateada,  # NUEVO
        estadisticas=estadisticas,
        proxima_cita=proxima_cita_info,
        fecha_actual_formateada=fecha_actual_formateada,
        estadisticas_plan=estadisticas_plan,
        total_citas_semana=total_citas_semana,
        limite_citas_visibles=LIMITE_CITAS_VISIBLES,
    )



@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username_o_email = request.form.get('usuario')
        contrasena = request.form.get('contrasena')
        
        usuario_encontrado = Usuario.query.filter(
            (Usuario.username == username_o_email) | (Usuario.email == username_o_email)
        ).first()
        
        if usuario_encontrado and usuario_encontrado.check_password(contrasena):

            login_user(usuario_encontrado, remember=request.form.get('remember_me') is not None)
            flash('Has iniciado sesión correctamente.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('Credenciales inválidas. Por favor, verifica tu usuario y contraseña.', 'danger')

    return render_template('login.html')



@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('main.login'))

@main_bp.route('/home') 
def ruta_a_inicio(): 
    return redirect(url_for('main.dashboard'))

@main_bp.route('/perfil', methods=['GET', 'POST'])
@login_required 
def perfil():
    usuario_a_editar = current_user

    if request.method == 'POST':
        nombre_completo = request.form.get('nombre_completo', '').strip()
        email = request.form.get('email', '').strip().lower()
        
        if not nombre_completo or not email:
            flash('El nombre y el email no pueden estar vacíos.', 'danger')
            return render_template('perfil.html', usuario=usuario_a_editar)

        if email != usuario_a_editar.email and Usuario.query.filter_by(email=email).first():
            flash('Ese correo electrónico ya está en uso por otra cuenta.', 'danger')
            return render_template('perfil.html', usuario=usuario_a_editar)

        usuario_a_editar.nombre_completo = nombre_completo
        usuario_a_editar.email = email
        
        password_actual = request.form.get('password_actual')
        password_nueva = request.form.get('password_nueva')
        if password_actual and password_nueva:
            if usuario_a_editar.check_password(password_actual):
                usuario_a_editar.set_password(password_nueva)
                flash('Contraseña actualizada correctamente.', 'info')
            else:
                flash('La contraseña actual es incorrecta.', 'danger')
                return render_template('perfil.html', usuario=usuario_a_editar)

        try:
            db.session.commit()
            flash('Perfil actualizado exitosamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error al actualizar el perfil: {e}', 'danger')
        
        return redirect(url_for('main.perfil'))

    return render_template('perfil.html', usuario=usuario_a_editar)

@main_bp.route('/test')
@login_required
def test():
    return render_template('test.html')


@main_bp.route('/registro', methods=['GET', 'POST'])
def registro():

 
    
    plan_nombre = request.args.get('plan', 'trial')
    plan = Plan.query.filter_by(nombre=plan_nombre, activo=True).first()
    
    if not plan:
        flash('Plan no válido', 'danger')
        return redirect(url_for('main.inicio'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        plan_recibido = request.form.get('plan', 'trial')
        
        # Validar campos
        if not all([username, email, password, confirm_password]):
            flash('Todos los campos son obligatorios', 'danger')
            return render_template('registro.html', plan=plan)
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'danger')
            return render_template('registro.html', plan=plan)
        
        # Verificar si ya existe
        if Usuario.query.filter_by(email=email).first():
            flash('Este email ya está registrado', 'danger')
            return render_template('registro.html', plan=plan)
        
        if Usuario.query.filter_by(username=username).first():
            flash('Este nombre de usuario ya existe', 'danger')
            return render_template('registro.html', plan=plan)
        
        # Crear usuario
        nuevo_usuario = Usuario(
            username=username,
            email=email,
            nombre_completo=request.form.get('nombre_completo', ''),
            is_admin=False
        )
        nuevo_usuario.set_password(password)
        db.session.add(nuevo_usuario)
        db.session.flush()
        
        colombia_tz = pytz.timezone('America/Bogota')
        ahora = datetime.now(colombia_tz)
        
        if plan.nombre == 'trial':
            usuario_plan = UsuarioPlan(
                usuario_id=nuevo_usuario.id,
                plan_id=plan.id,
                estado='activo',
                fecha_inicio=ahora,
                fecha_fin=ahora + timedelta(days=7),
                es_trial=True,
                trial_dias_restantes=7
            )
            db.session.add(usuario_plan)
            db.session.commit()
            flash('¡Registro exitoso! Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('main.login'))
        
        else:
            # Plan de pago: crear solicitud de pago
            solicitud = SolicitudPago(
                user_id=nuevo_usuario.id,
                plan_id=plan.id,
                plan_nombre=plan.nombre,
                monto_cop=plan.precio_cop,
                estado='PENDIENTE'
            )
            db.session.add(solicitud)
            db.session.commit()
            
            flash('Registro exitoso. Completa el pago para activar tu plan.', 'info')
            return redirect(url_for('planes.instrucciones_pago', solicitud_id=solicitud.id))
    
    return render_template('registro.html', plan=plan)


@main_bp.route('/test-simple')
@login_required
def test_simple():
    return render_template('test_simple.html')

@main_bp.route('/terminos')
def terminos():
    return render_template('public/terminos.html')

@main_bp.route('/privacidad')
def privacidad():
    return render_template('public/privacidad.html')



@main_bp.route('/health', methods=['GET'])
def health_check():
    """Endpoint para health checks de Cloud Run"""
    try:
        # Verificar conexión a base de datos
        db.session.execute(text('SELECT 1'))  # 👈 CAMBIA ESTO
        db_status = 'ok'
    except Exception as e:
        db_status = 'error'
        current_app.logger.error(f"Health check DB error: {e}")
    
    return {
        'status': 'ok' if db_status == 'ok' else 'degraded',
        'database': db_status,
        'timestamp': datetime.utcnow().isoformat()
    }, 200 if db_status == 'ok' else 500
