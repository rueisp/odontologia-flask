# ▼▼▼ IMPORTACIONES COMPLETAS ▼▼▼
from flask import Blueprint, render_template, current_app, flash, request, redirect, url_for
from flask_login import login_required, current_user, login_user, logout_user
from datetime import datetime
import pytz
from clinica.utils import get_index_panel_data
# Importamos los modelos (Ya no necesitamos AuditLog aquí)
from clinica.models import Cita, Paciente, Factura, Usuario
from clinica import db

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
@login_required
def index():
    # 1. Fecha
    local_timezone = pytz.timezone('America/Bogota')
    now_in_local_tz = datetime.now(local_timezone)
    fecha_actual_formateada = now_in_local_tz.strftime('%A, %d de %B de %Y')
    
    # 2. Datos del Panel (Contadores)
    try:
        panel_data = get_index_panel_data(now_in_local_tz.date(), now_in_local_tz.time())
    except Exception as e:
        current_app.logger.error(f"Error panel: {e}")
        panel_data = {}

    # 3. Facturas Recientes (Sin desempaquetar nada raro, solo objetos)
    facturas_recientes = []
    try:
        facturas_db = Factura.query.order_by(Factura.fecha_factura.desc()).limit(5).all()
        for f in facturas_db:
            paciente_nombre = "Desconocido"
            if f.paciente:
                paciente_nombre = f"{f.paciente.nombres} {f.paciente.apellidos}"
            
            facturas_recientes.append({
                'id': f.id,
                'paciente_id': f.paciente_id,
                'nombre_paciente': paciente_nombre,
                'fecha_obj': f.fecha_factura,
                'citas_count': f.citas.count(),
                'total': f.valor_total
            })
    except Exception as e:
        current_app.logger.error(f"Error facturas: {e}")

    # 4. Estadísticas de plan y límites (NUEVO)
    from clinica.services.plan_service import PlanService
    estadisticas_plan = PlanService.obtener_estadisticas_usuario(current_user.id)    

    # Retorno limpio
    return render_template(
        "index.html",
        facturas_recientes=facturas_recientes,
        fecha_actual_formateada=fecha_actual_formateada,
        estadisticas_plan=estadisticas_plan,  # ← NUEVO
        **panel_data
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

# Agrega esto al final de tu main.py o en una ruta temporal:
@main_bp.route('/debug-rutas')
def debug_rutas():
    from flask import current_app
    rutas = []
    for rule in current_app.url_map.iter_rules():
        rutas.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'rule': rule.rule
        })
    
    # Ordenar por ruta
    rutas.sort(key=lambda x: x['rule'])
    
    html = "<h1>Rutas registradas en Flask</h1><ul>"
    for ruta in rutas:
        html += f"<li><strong>{ruta['rule']}</strong> → {ruta['endpoint']} ({', '.join(ruta['methods'])})</li>"
    html += "</ul>"
    
    return html