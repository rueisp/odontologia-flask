# clinica/__init__.py

import os
from flask import Flask, request
from .extensions import db, migrate, login_manager 
import cloudinary
from dotenv import load_dotenv # <--- Lo usaremos solo para el .env local
import logging
import datetime
from flask.json import dumps as json_dumps

# --- IMPORTANTE: Cargar dotenv solo si estamos en un contexto local y .env existe ---
# Esto evita que Render intente cargar un .env que no existe.
if os.path.exists('.env'):
    load_dotenv()

# ===========================================================================
# MODIFICACIONES AÑADIDAS AQUÍ PARA LA FUNCIÓN GLOBAL JINJA (se mantiene)
# ===========================================================================

def get_attr_safe(obj, attr_name, default_value=None):
    """
    Función global Jinja personalizada para obtener de forma segura un atributo de un objeto.
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
    
    app = Flask(__name__, instance_relative_config=True) 

    # --- 1. CONFIGURACIÓN DE LA APP ---
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(24).hex()), 
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///instance/clinica.db'), 
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_POOL_RECYCLE=60,
        SQLALCHEMY_POOL_SIZE=5,
        SQLALCHEMY_ENGINE_OPTIONS={
            'pool_pre_ping': True
        },
        CLOUDINARY_CLOUD_NAME=os.environ.get('CLOUDINARY_CLOUD_NAME'),
        CLOUDINARY_API_KEY=os.environ.get('CLOUDINARY_API_KEY'),
        CLOUDINARY_API_SECRET=os.environ.get('CLOUDINARY_API_SECRET'),
        CLOUDINARY_SECURE=True, 
        DEBUG=os.environ.get('FLASK_DEBUG') == '1' 
    )

    app.config['SESSION_COOKIE_SECURE'] = app.config['DEBUG'] == False 
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    if app.config['DEBUG']:
        app.config['SQLALCHEMY_ECHO'] = True
        logging.getLogger('sqlalchemy.pool').setLevel(logging.DEBUG)
        logging.getLogger('sqlalchemy.dialects').setLevel(logging.DEBUG)
        logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)
    else:
        app.config['SQLALCHEMY_ECHO'] = False

    if not app.debug:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
    else: 
        app.logger.setLevel(logging.DEBUG)

    app.logger.info(f"Application initialized. DEBUG={app.debug}. Logging level set to {app.logger.level}.")

    if app.config.get('CLOUDINARY_CLOUD_NAME') and \
       app.config.get('CLOUDINARY_API_KEY') and \
       app.config.get('CLOUDINARY_API_SECRET'):
        cloudinary.config(
            cloud_name=app.config.get('CLOUDINARY_CLOUD_NAME'),
            api_key=app.config.get('CLOUDINARY_API_KEY'),
            api_secret=app.config.get('CLOUDINARY_API_SECRET'),
            secure=app.config.get('CLOUDINARY_SECURE', True) 
        )
        app.logger.info("Cloudinary configured using environment variables.")
    else:
        app.logger.warning("CLOUDINARY: Credenciales no configuradas. Las funciones de Cloudinary pueden fallar.")

    @app.after_request
    def add_cors_headers(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
        
        if 'Cache-Control' not in response.headers:
             response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
             response.headers['Pragma'] = 'no-cache'
             response.headers['Expires'] = '0'

        return response


    # --- 2. INICIALIZAR EXTENSIONES CON LA APP ---
    db.init_app(app)
    migrate.init_app(app, db) # Flask-Migrate con Alembic
    login_manager.init_app(app)

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
    with app.app_context(): 
        # db.create_all() # <--- ¡AHORA SÍ, COMENTA ESTA LÍNEA!
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

        # ==============================================================
        # *** NUEVO: RUTA PARA MANTENER LA APP VIVA (PING) ***
        # ==============================================================
        @app.route('/awake')
        def awake():
            # Este endpoint responderá a GitHub Actions para mantener Render activo
            return "Render App Awake", 200
        # ==============================================================
        
        
    return app

app = create_app()