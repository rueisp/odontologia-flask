# clinica/__init__.py

import os
from flask import Flask, request
from .extensions import db, migrate, login_manager # ¡migrate está aquí, lo cual es bueno!
import cloudinary
from dotenv import load_dotenv # Lo usaremos condicionalmente para desarrollo
import logging
import datetime
from flask.json import dumps as json_dumps

# --- IMPORTANTES: Cargar dotenv condicionalmente ---
# load_dotenv() # <--- MOVIDO: No cargues esto directamente aquí para producción
                 # Render no usa .env, sino variables de entorno directas.
                 # Esto solo lo usaremos en run.py para el ambiente local.

# ===========================================================================
# MODIFICACIONES AÑADIDAS AQUÍ PARA LA FUNCIÓN GLOBAL JINJA
# ===========================================================================

def get_attr_safe(obj, attr_name, default_value=None):
    """
    Función global Jinja personalizada para obtener de forma segura un atributo de un objeto.
    Utiliza la función getattr incorporada de Python, que es más robusta.
    Maneja tanto objetos como diccionarios.
    """
    if obj is None:
        return default_value
    if isinstance(obj, dict):
        return obj.get(attr_name, default_value)
    else:
        return getattr(obj, attr_name, default_value)

# ===========================================================================
# FIN DE MODIFICACIONES
# ===========================================================================


def create_app():
    """Application Factory Function"""
    
    # --- 1. CONFIGURACIÓN DE LA APP ---
    app = Flask(__name__, instance_relative_config=True) # <-- AÑADIDO: instance_relative_config=True

    # Configuración base desde variables de entorno con fallbacks para desarrollo
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(24).hex()), # ¡GENERA UNA CLAVE SEGURA AQUÍ PARA DEV SI NO HAY EN ENTORNO!
        # DATABASE_URL será provista por Render. Para local, usa un valor por defecto.
        # Ajusta la ruta de sqlite si tu carpeta instance no está en la raíz.
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///instance/clinica.db'), 
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_POOL_RECYCLE=60,
        SQLALCHEMY_POOL_SIZE=5,
        SQLALCHEMY_ENGINE_OPTIONS={
            'pool_pre_ping': True
        },
        # Configuración de Cloudinary (desde variables de entorno)
        CLOUDINARY_CLOUD_NAME=os.environ.get('CLOUDINARY_CLOUD_NAME'),
        CLOUDINARY_API_KEY=os.environ.get('CLOUDINARY_API_KEY'),
        CLOUDINARY_API_SECRET=os.environ.get('CLOUDINARY_API_SECRET'),
        CLOUDINARY_SECURE=True, # Asegúrate de que esto también se lea del entorno si es posible
        # Modo de depuración: desactivar en Render
        DEBUG=os.environ.get('FLASK_DEBUG') == '1' # Lee FLASK_DEBUG del entorno
    )

    # --- Ajustes de Sesión (usar cookies seguras solo en HTTPS/producción) ---
    app.config['SESSION_COOKIE_SECURE'] = app.config['DEBUG'] == False # True en producción, False en dev
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


    # --- Configuración de Logging de SQLAlchemy (Opcional) ---
    if app.config['DEBUG']: # Solo habilita logging detallado en desarrollo
        app.config['SQLALCHEMY_ECHO'] = True
        logging.getLogger('sqlalchemy.pool').setLevel(logging.DEBUG)
        logging.getLogger('sqlalchemy.dialects').setLevel(logging.DEBUG)
        logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)
    else:
        app.config['SQLALCHEMY_ECHO'] = False # Desactiva en producción

    # --- Configuración del Logger General de Flask ---
    # Render captura stdout/stderr, así que un StreamHandler es ideal.
    if not app.debug: # Configurar logging INFO para producción
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
    else: # Configurar logging DEBUG para desarrollo
        app.logger.setLevel(logging.DEBUG)

    app.logger.info(f"Application initialized. DEBUG={app.debug}. Logging level set to {app.logger.level}.")


    # --- Configuración de Cloudinary ---
    # Solo inicializar si las credenciales están disponibles
    if app.config.get('CLOUDINARY_CLOUD_NAME') and \
       app.config.get('CLOUDINARY_API_KEY') and \
       app.config.get('CLOUDINARY_API_SECRET'):
        cloudinary.config(
            cloud_name=app.config.get('CLOUDINARY_CLOUD_NAME'),
            api_key=app.config.get('CLOUDINARY_API_KEY'),
            api_secret=app.config.get('CLOUDINARY_API_SECRET'),
            secure=app.config.get('CLOUDINARY_SECURE', True) # Por defecto a True
        )
        app.logger.info("Cloudinary configured using environment variables.")
    else:
        app.logger.warning("CLOUDINARY: Credenciales no configuradas. Las funciones de Cloudinary pueden fallar.")


    # --- Directorios de Subida (Asegúrate que sean relativos al proyecto o configurables) ---
    # En Render, no se garantiza que la estructura de archivos sea persistente o modificable fuera de /tmp.
    # Si estas carpetas son para almacenar archivos físicamente en el servidor (no en Cloudinary),
    # Render no las conservará entre despliegues o reinicios.
    # Si son carpetas *locales* de static para desarrollo, está bien.
    # Si son solo para las rutas, está bien.
    # Si solo usas Cloudinary, estos directorios físicos no son tan críticos para producción.
    # os.makedirs(os.path.join(app.static_folder, 'img', 'pacientes', 'dentigramas'), exist_ok=True)
    # os.makedirs(os.path.join(app.static_folder, 'img', 'pacientes', 'imagenes'), exist_ok=True)
    # app.logger.info("Directorios de subida locales verificados/creados.")


    @app.after_request
    def add_cors_headers(response):
        # CORS puede necesitar ajustarse si tu frontend está en un dominio diferente.
        # '*' es para todos, pero puedes especificar dominios (ej. 'https://tufrontend.com').
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
        
        # Cache-Control: no-cache es bueno para desarrollo, pero en producción
        # querrás cachear assets estáticos si es posible. Para HTML y APIs, es a menudo adecuado.
        if 'Cache-Control' not in response.headers:
             response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
             response.headers['Pragma'] = 'no-cache'
             response.headers['Expires'] = '0'

        return response


    # --- 2. INICIALIZAR EXTENSIONES CON LA APP ---
    db.init_app(app)
    migrate.init_app(app, db) # Flask-Migrate con Alembic
    login_manager.init_app(app)

    # Configurar el user_loader para Flask-Login (¡MOVIDO AQUÍ!)
    # Debe estar disponible antes de registrar blueprints que lo usen
    from .models import Usuario 
    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))
    
    login_manager.login_view = 'main.login'
    login_manager.login_message = "Por favor, inicia sesión para acceder a esta página."
    login_manager.login_message_category = "warning"


    # --- REGISTRA LA FUNCIÓN GLOBAL JINJA AQUÍ ---
    app.jinja_env.globals['get_attr'] = get_attr_safe
    app.logger.debug("Jinja global 'get_attr' registered.")
    
    # --- REGISTRAR EL FILTRO 'tojson' DE FORMA EXPLÍCITA ---
    app.jinja_env.add_extension('jinja2.ext.do')
    app.jinja_env.filters['tojson'] = json_dumps 
    app.logger.debug("Jinja filter 'tojson' explicitly registered.")


    # --- 3. REGISTRAR BLUEPRINTS (RUTAS) ---
    with app.app_context(): # Es una buena práctica registrar blueprints dentro del app_context
        # Importa tus modelos aquí si los blueprints los necesitan antes de su registro
        # (aunque si los blueprints importan los modelos, no es estrictamente necesario aquí)
        from .routes.main import main_bp
        from .routes.pacientes import pacientes_bp
        from .routes.pacientes_evoluciones import evoluciones_bp
        from .routes.pacientes_ajax import ajax_bp
        from .routes.pacientes_citas import citas_paciente_bp 
        from .routes.calendario import calendario_bp
        from .routes.export import export_bp
        from .routes.papelera import papelera_bp

        app.register_blueprint(main_bp)
        app.register_blueprint(pacientes_bp)
        app.register_blueprint(evoluciones_bp)
        app.register_blueprint(ajax_bp)
        app.register_blueprint(citas_paciente_bp)
        app.register_blueprint(calendario_bp, url_prefix='/calendario')
        app.register_blueprint(export_bp, url_prefix='/export')
        app.register_blueprint(papelera_bp, url_prefix='/papelera')
        
    return app