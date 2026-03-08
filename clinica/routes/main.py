# ▼▼▼ IMPORTACIONES COMPLETAS ▼▼▼
from flask import Blueprint, render_template, current_app, flash, request, redirect, url_for
from flask_login import login_required, current_user, login_user, logout_user
from datetime import datetime, timedelta, time
import pytz
# Importamos los modelos necesarios SOLAMENTE
from clinica.models import Cita, Paciente, Usuario
from clinica import db
from sqlalchemy import func, extract
from sqlalchemy.orm import load_only

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
@login_required
def index():
    # 1. Fecha y Hora Local
    local_timezone = pytz.timezone('America/Bogota')
    now_in_local_tz = datetime.now(local_timezone)
    fecha_actual_formateada = now_in_local_tz.strftime('%A, %d de %B de %Y')
    
    # 2. CITAS DE HOY - OPTIMIZADAS (sin RIPS)
    hoy_date = now_in_local_tz.date()
    citas_hoy = Cita.query.options(
        load_only(
            Cita.id, 
            Cita.paciente_id, 
            Cita.hora, 
            Cita.motivo, 
            Cita.doctor, 
            Cita.estado,
            Cita.paciente_nombres_str,
            Cita.paciente_apellidos_str
        )
    ).filter(
        Cita.fecha == hoy_date,
        Cita.is_deleted == False,
        Cita.odontologo_id == current_user.id
    ).order_by(Cita.hora).all()
    
    # Procesar citas para el template
    citas_procesadas = []
    paciente_ids = list(set([c.paciente_id for c in citas_hoy if c.paciente_id]))
    
    # Cargar nombres de pacientes en una sola consulta
    pacientes_dict = {}
    if paciente_ids:
        pacientes = Paciente.query.options(
            load_only(Paciente.id, Paciente.nombres, Paciente.apellidos)
        ).filter(Paciente.id.in_(paciente_ids)).all()
        for p in pacientes:
            pacientes_dict[p.id] = p
    
    for cita in citas_hoy:
        if cita.paciente_id and cita.paciente_id in pacientes_dict:
            paciente = pacientes_dict[cita.paciente_id]
            nombre_completo = f"{paciente.nombres} {paciente.apellidos}".strip()
        else:
            nombre_completo = f"{cita.paciente_nombres_str or ''} {cita.paciente_apellidos_str or ''}".strip()
            if not nombre_completo:
                nombre_completo = "Paciente sin registrar"
        
        citas_procesadas.append({
            'id': cita.id,
            'paciente_nombre_completo': nombre_completo,
            'hora_formateada': cita.hora.strftime('%I:%M %p'),
            'motivo': cita.motivo or 'Consulta',
            'doctor': cita.doctor,
            'estado': cita.estado
        })
    
    # 3. CONTADOR SEMANAL (CORREGIDO Y OPTIMIZADO)
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
    
    # 4. PRÓXIMA CITA (opcional, para el panel)
    proxima_cita = Cita.query.options(
        load_only(Cita.id, Cita.fecha, Cita.hora, Cita.paciente_id, Cita.paciente_nombres_str, Cita.paciente_apellidos_str)
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
            paciente_nombre = f"{proxima_cita.paciente_nombres_str or ''} {proxima_cita.paciente_apellidos_str or ''}".strip() or "Paciente"
        
        proxima_cita_info = {
            'fecha_formateada': proxima_cita.fecha.strftime('%d/%m/%Y'),
            'hora': proxima_cita.hora.strftime('%H:%M'),
            'paciente_nombre': paciente_nombre
        }
    
    # 5. Estadísticas de plan y límites (si es necesario)
    from clinica.services.plan_service import PlanService
    estadisticas_plan = PlanService.obtener_estadisticas_usuario(current_user.id)
    
    return render_template(
        "index.html",
        citas_del_dia=citas_procesadas,
        proxima_cita=proxima_cita_info,
        fecha_actual_formateada=fecha_actual_formateada,
        estadisticas_plan=estadisticas_plan,
        total_citas_semana=total_citas_semana,
        # Eliminamos facturas_recientes completamente
    )

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

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
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Credenciales inválidas. Por favor, verifica tu usuario y contraseña.', 'danger')

    return render_template('login.html')

@main_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not all([username, email, password, confirm_password]):
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('registro.html')

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('registro.html')

        if Usuario.query.filter_by(username=username).first():
            flash('El nombre de usuario ya está en uso. Por favor, elige otro.', 'danger')
            return render_template('registro.html')

        if Usuario.query.filter_by(email=email).first():
            flash('El correo electrónico ya está registrado.', 'danger')
            return render_template('registro.html')

        nuevo_usuario = Usuario(
            username=username, 
            email=email, 
            is_admin=False 
        )
        nuevo_usuario.set_password(password) 

        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al registrar nuevo usuario: {e}", exc_info=True)
            flash("Ocurrió un error al crear la cuenta. Por favor, inténtalo más tarde.", 'danger')
            return render_template('registro.html')

        flash('¡Tu cuenta ha sido creada exitosamente! Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('main.login'))

    return render_template('registro.html')

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('main.login'))

@main_bp.route('/home') 
def ruta_a_inicio(): 
    return redirect(url_for('main.index'))

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

