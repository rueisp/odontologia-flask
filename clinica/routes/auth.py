# clinica/routes/auth.py

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app
)
from flask_login import login_user, logout_user, login_required, current_user

# Importa el objeto 'db' de tu archivo de extensiones
from ..extensions import db 
# Importa los modelos que necesitarás
from ..models import Usuario, AuditLog, Cita, Paciente

# Importa funciones auxiliares que estaban en app.py (si las necesitas aquí)
# Si get_index_panel_data sigue siendo muy grande, podría vivir en un archivo 'utils.py'
from sqlalchemy import func, case, or_
from sqlalchemy.orm import joinedload
from datetime import date, datetime
import locale

# --- Definición del Blueprint ---
# 'main' es el nombre que usaremos en url_for, ej: url_for('main.index')
main_bp = Blueprint('main', __name__, template_folder='../templates')


def get_index_panel_data():
    """
    Función para obtener los datos necesarios para el panel de inicio.
    Esta función ahora es parte de este blueprint.
    """
    # ... (Copiamos la función completa aquí, pero con una mejora clave) ...
    # Usamos current_app.logger en lugar de app.logger
    
    hoy = date.today()
    datos_panel = {}

    # 1. Fecha actual formateada (simplificada)
    meses = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
        5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
        9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
    }
    dias = {
        0: 'lunes', 1: 'martes', 2: 'miércoles', 3: 'jueves',
        4: 'viernes', 5: 'sábado', 6: 'domingo'
    }
    
    try:
        dia_semana = dias[hoy.weekday()]
        mes = meses[hoy.month]
        fecha_formateada = f"{dia_semana.capitalize()}, {hoy.day} de {mes} de {hoy.year}"
    except Exception as e:
        current_app.logger.error(f"Error al formatear fecha: {e}")
        fecha_formateada = hoy.strftime("%Y-%m-%d")
    
    datos_panel['fecha_actual_formateada'] = fecha_formateada

    # 2. Estadísticas: Citas de hoy
    citas_hoy_count = db.session.query(func.count(Cita.id))\
        .join(Paciente, Cita.paciente_id == Paciente.id)\
        .filter(
            Cita.fecha == hoy,
            Cita.is_deleted == False,
            Paciente.is_deleted == False
        ).scalar() or 0
    datos_panel['estadisticas'] = {'citas_hoy': citas_hoy_count}
    
    # ... (El resto de la lógica de get_index_panel_data sigue aquí sin cambios)...
    # Asegúrate de que todas las dependencias como Cita, Paciente, db, etc., estén importadas.
    # Esta es una versión abreviada para no pegar todo de nuevo.
    # Solo pega el resto de tu función original aquí.
    
    # Ejemplo del final de la función
    citas_de_hoy_lista = Cita.query.options(joinedload(Cita.paciente))\
        .join(Paciente, Cita.paciente_id == Paciente.id)\
        .filter(Cita.fecha == hoy, Cita.is_deleted == False, Paciente.is_deleted == False)\
        .order_by(Cita.hora).all()
        
    citas_hoy_procesadas = []
    for cita_item in citas_de_hoy_lista:
        citas_hoy_procesadas.append({
            'id': cita_item.id,
            'hora_formateada': cita_item.hora.strftime("%I:%M %p"), 
            'paciente_nombre_completo': f"{cita_item.paciente.nombres} {cita_item.paciente.apellidos}",
            'motivo': getattr(cita_item, 'motivo', "No especificado"),
            'estado': getattr(cita_item, 'estado', 'pendiente')
        })
    datos_panel['citas_del_dia'] = citas_hoy_procesadas

    return datos_panel


# --- Definición de las Rutas usando el Blueprint ---

@main_bp.route("/")
@login_required # ¡Protegemos la página principal!
def index():
    try:
        panel_data = get_index_panel_data() 
    except Exception as e:
        current_app.logger.error(f"Error al obtener datos del panel: {e}", exc_info=True)
        panel_data = {}
        flash("Hubo un error al cargar los datos del panel de inicio.", "danger")

    try:
        ultimas_acciones = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(5).all()
    except Exception as e:
        current_app.logger.error(f"Error al obtener las últimas acciones de auditoría: {e}", exc_info=True)
        ultimas_acciones = []

    template_data = {
        **panel_data,
        'ultimas_acciones': ultimas_acciones
        # 'current_user' ya está disponible globalmente en las plantillas gracias a Flask-Login
    }
    
    return render_template("index.html", **template_data)


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index')) # Apunta a la función 'index' dentro del blueprint 'main'

    if request.method == 'POST':
        username_o_email = request.form.get('usuario')
        contrasena = request.form.get('contrasena')
        remember_me = request.form.get('remember_me') is not None 

        if not username_o_email or not contrasena:
            flash('Por favor, ingresa tu usuario y contraseña.', 'warning')
            return render_template('login.html')

        # La consulta a la DB usa el objeto 'db' que importamos
        usuario_encontrado = Usuario.query.filter(
            or_(Usuario.username == username_o_email, Usuario.email == username_o_email)
        ).first()
        
        if usuario_encontrado and usuario_encontrado.check_password(contrasena):
            login_user(usuario_encontrado, remember=remember_me)
            
            # Log de seguridad: login exitoso
            current_app.logger.info(f"Login exitoso: usuario='{usuario_encontrado.username}', IP={request.remote_addr}")
            
            flash('Has iniciado sesión correctamente.', 'success')
            
            next_page = request.args.get('next')
            # Redirigir a 'next_page' o al index si no hay 'next'
            return redirect(next_page or url_for('main.index'))
        else:
            # Log de seguridad: login fallido
            current_app.logger.warning(f"Intento de login fallido: usuario/email='{username_o_email}', IP={request.remote_addr}")
            
            flash('Credenciales inválidas. Por favor, verifica tu usuario y contraseña.', 'danger')

    return render_template('login.html')


@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('main.login')) # Redirige a la página de login del blueprint 'main'

