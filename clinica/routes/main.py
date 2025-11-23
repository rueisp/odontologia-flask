# ▼▼▼ IMPORTACIONES COMPLETAS (Incluyendo request, redirect, url_for) ▼▼▼
from flask import Blueprint, render_template, current_app, flash, request, redirect, url_for
from flask_login import login_required, current_user, login_user, logout_user
from datetime import datetime
import pytz
from clinica.utils import get_index_panel_data
# Importamos los modelos
from clinica.models import Cita, Paciente, Factura, Usuario # Asegúrate de importar User si lo usas en login
from clinica import db
# ▼▼▼ ESTA ES LA LÍNEA QUE FALTABA ▼▼▼
main_bp = Blueprint('main', __name__)

@main_bp.route("/")
@login_required
def index():
    # --- 1. CONFIGURACIÓN BÁSICA ---
    local_timezone = pytz.timezone('America/Bogota')
    now_in_local_tz = datetime.now(local_timezone)
    
    fecha_actual_formateada = now_in_local_tz.strftime('%A, %d de %B de %Y')
    fecha_actual_corta = now_in_local_tz.strftime('%d %B')

    # --- 2. DATOS DEL PANEL ---
    try:
        panel_data = get_index_panel_data(now_in_local_tz.date(), now_in_local_tz.time())
    except Exception as e:
        current_app.logger.error(f"Error panel: {e}")
        panel_data = {}

    # --- 3. LÓGICA DE FACTURAS (LIMPIA) ---
    lista_facturas_simple = []
    
    try:
        facturas_db = Factura.query.order_by(Factura.fecha_factura.desc()).limit(5).all()
        
        for f in facturas_db:
            # 1. Buscar Paciente y Nombre de forma segura (Singular o Plural)
            try:
                paciente = Paciente.query.get(f.paciente_id)
                if paciente:
                    # Intenta 'nombres', si falla intenta 'nombre', si falla pone 'Desconocido'
                    p_nombre = getattr(paciente, 'nombres', getattr(paciente, 'nombre', ''))
                    p_apellido = getattr(paciente, 'apellidos', getattr(paciente, 'apellido', ''))
                    nombre_completo = f"{p_nombre} {p_apellido}".strip() or "Paciente Sin Nombre"
                else:
                    nombre_completo = "Paciente Eliminado"
            except AttributeError:
                nombre_completo = "Error de Datos"
            
            # 2. Contar citas de forma segura
            try:
                num_citas = f.citas.count() 
            except AttributeError:
                num_citas = 0
                
            # 3. Crear diccionario simple
            datos = {
                'id': f.id,
                'paciente_id': f.paciente_id,
                'nombre_paciente': nombre_completo,
                'fecha_obj': f.fecha_factura,
                'citas_count': num_citas,
                'total': f.valor_total
            }
            lista_facturas_simple.append(datos)
            
    except Exception as e:
        current_app.logger.error(f"Error al cargar facturas: {e}")

    return render_template(
        "index.html",
        facturas_recientes=lista_facturas_simple,
        fecha_actual_formateada=fecha_actual_formateada,
        fecha_actual_corta=fecha_actual_corta,
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


# --- ▼▼▼ INICIO DE LA NUEVA RUTA DE REGISTRO ▼▼▼ ---
@main_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    # Si el usuario ya está logueado, que no pueda acceder a la página de registro
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        # 1. Obtener datos del formulario de registro
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # 2. Validaciones de los datos
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

        # 3. Si todo es válido, crear el nuevo usuario
        # Por defecto, los nuevos usuarios no son administradores (is_admin=False)
        nuevo_usuario = Usuario(
            username=username, 
            email=email, 
            is_admin=False # Importante: no permitir que los usuarios se hagan admin a sí mismos
        )
        nuevo_usuario.set_password(password) # Encriptar la contraseña

        # 4. Guardar en la base de datos
        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al registrar nuevo usuario: {e}", exc_info=True)
            flash("Ocurrió un error al crear la cuenta. Por favor, inténtalo más tarde.", 'danger')
            return render_template('registro.html')

        # 5. Informar al usuario y redirigir a la página de login
        flash('¡Tu cuenta ha sido creada exitosamente! Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('main.login'))

    # Si el método es GET, simplemente muestra la página de registro
    return render_template('registro.html')
# --- ▲▲▲ FIN DE LA NUEVA RUTA DE REGISTRO ▲▲▲ ---


@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('main.login'))


# Esta ruta es redundante, pero se mantiene por si se usa en algún lado
@main_bp.route('/home') 
def ruta_a_inicio(): 
    return redirect(url_for('main.index'))

# En routes/main.py

# ... (importaciones existentes) ...

# --- NUEVA RUTA PARA EL PERFIL DEL USUARIO ---
@main_bp.route('/perfil', methods=['GET', 'POST'])
@login_required # Solo usuarios logueados pueden ver su perfil
def perfil():
    # No necesitamos un ID, 'current_user' ya nos dice quién es el usuario
    usuario_a_editar = current_user

    if request.method == 'POST':
        # 1. Obtener los datos del formulario
        nombre_completo = request.form.get('nombre_completo', '').strip()
        email = request.form.get('email', '').strip().lower()
        
        # 2. Validaciones
        if not nombre_completo or not email:
            flash('El nombre y el email no pueden estar vacíos.', 'danger')
            return render_template('perfil.html', usuario=usuario_a_editar)

        # Verificar si el nuevo email ya está en uso por OTRO usuario
        if email != usuario_a_editar.email and Usuario.query.filter_by(email=email).first():
            flash('Ese correo electrónico ya está en uso por otra cuenta.', 'danger')
            return render_template('perfil.html', usuario=usuario_a_editar)

        # 3. Actualizar los datos del usuario
        usuario_a_editar.nombre_completo = nombre_completo
        usuario_a_editar.email = email
        
        # Opcional: Cambiar contraseña
        password_actual = request.form.get('password_actual')
        password_nueva = request.form.get('password_nueva')
        if password_actual and password_nueva:
            if usuario_a_editar.check_password(password_actual):
                usuario_a_editar.set_password(password_nueva)
                flash('Contraseña actualizada correctamente.', 'info')
            else:
                flash('La contraseña actual es incorrecta.', 'danger')
                return render_template('perfil.html', usuario=usuario_a_editar)

        # 4. Guardar en la base de datos
        try:
            db.session.commit()
            flash('Perfil actualizado exitosamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error al actualizar el perfil: {e}', 'danger')
        
        return redirect(url_for('main.perfil'))

    # Para el método GET, simplemente muestra la plantilla con los datos del usuario
    return render_template('perfil.html', usuario=usuario_a_editar)