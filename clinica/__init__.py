# clinica/__init__.py

import os
from flask import Flask, request
from .extensions import db, migrate, login_manager
import cloudinary
from dotenv import load_dotenv
import logging
import datetime # <--- ¡AÑADIR ESTA IMPORTACIÓN!
from flask.json import dumps as json_dumps # <-- ¡AÑADIR ESTA IMPORTACIÓN!

# Cargar automáticamente las variables definidas en .env
load_dotenv()

# ===========================================================================
# MODIFICACIONES AÑADIDAS AQUÍ PARA LA FUNCIÓN GLOBAL JINJA
# ===========================================================================

# Define la función Python que actuará como nuestro `get_attr` personalizado
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
    
    app = Flask(__name__)

    # --- 1. CONFIGURACIÓN DE LA APP ---
    app.config['SECRET_KEY'] = '23456'
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    app.config['SQLALCHEMY_POOL_RECYCLE'] = 60
    app.config['SQLALCHEMY_POOL_SIZE'] = 5
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True
    }
    
        # --- ¡OPCIONAL: HABILITAR LOGGING DEL POOL DE CONEXIONES! ---
    # Esto te dará mucha información sobre lo que hace el pool de conexiones
    app.config['SQLALCHEMY_ECHO'] = True # Muestra todas las sentencias SQL ejecutadas
    logging.getLogger('sqlalchemy.pool').setLevel(logging.DEBUG)
    logging.getLogger('sqlalchemy.dialects').setLevel(logging.DEBUG)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)
    # --- FIN OPCIONAL ---


    app.logger.setLevel(logging.DEBUG)
    app.logger.info("Application initialized. Logging level set to DEBUG.")

    app.config['UPLOAD_FOLDER_DENTIGRAMAS'] = os.path.join(app.static_folder, 'img', 'pacientes', 'dentigramas')
    app.config['UPLOAD_FOLDER_IMAGENES'] = os.path.join(app.static_folder, 'img', 'pacientes', 'imagenes')

    os.makedirs(app.config['UPLOAD_FOLDER_DENTIGRAMAS'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_IMAGENES'], exist_ok=True)
    
    cloudinary.config(
        cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'),
        api_key = os.environ.get('CLOUDINARY_API_KEY'),
        api_secret = os.environ.get('CLOUDINARY_API_SECRET'),
        secure = True
    )
    app.logger.info("Cloudinary configured using environment variables.")

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
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # --- REGISTRA LA FUNCIÓN GLOBAL JINJA AQUÍ ---
    # ¡IMPORTANTE! Esta línea es la que faltaba!
    app.jinja_env.globals['get_attr'] = get_attr_safe
    app.logger.debug("Jinja global 'get_attr' registered.")
    
    # --- ¡REGISTRAR EL FILTRO 'tojson' DE FORMA EXPLÍCITA! ---
    # Esto asegura que Flask use su propio tojson que sabe manejar objetos de Python
    app.jinja_env.add_extension('jinja2.ext.do') # Necesario para 'do' y a veces ayuda con otros filtros
    app.jinja_env.filters['tojson'] = json_dumps 
    app.logger.debug("Jinja filter 'tojson' explicitly registered.")
    # --- FIN DE REGISTRO DE FILTRO ---


    # --- 3. REGISTRAR BLUEPRINTS (RUTAS) ---
    with app.app_context():
        from .models import Usuario
        
        @login_manager.user_loader
        def load_user(user_id):
            return Usuario.query.get(int(user_id))

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