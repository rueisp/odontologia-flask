# clinica/__init__.py

import os
from flask import Flask
from .extensions import db, migrate, login_manager 
import cloudinary
from dotenv import load_dotenv
import logging
from flask.json import dumps as json_dumps
from .utils import get_transformed_profile_image_url

# Cargar .env solo localmente
if os.path.exists('.env'):
    load_dotenv()

# Función global Jinja
def get_attr_safe(obj, attr_name, default_value=None):
    if obj is None:
        return default_value
    if isinstance(obj, dict):
        return obj.get(attr_name, default_value)
    else:
        return getattr(obj, attr_name, default_value)

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
        SQLALCHEMY_ENGINE_OPTIONS={'pool_pre_ping': True},
        DEBUG=os.environ.get('FLASK_DEBUG') == '1' 
    )

    app.config['SESSION_COOKIE_SECURE'] = app.config['DEBUG'] == False 
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Logging setup
    if app.config['DEBUG']:
        app.config['SQLALCHEMY_ECHO'] = True
        logging.getLogger('sqlalchemy.pool').setLevel(logging.DEBUG)
    else:
        app.config['SQLALCHEMY_ECHO'] = False

    if not app.debug:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
    else: 
        app.logger.setLevel(logging.DEBUG)

    app.logger.info(f"App initialized. DEBUG={app.debug}.")

    # --- CORRECCIÓN CRÍTICA DE CLOUDINARY ---
    # Intentamos obtener la variable global
    cloudinary_url = os.environ.get('CLOUDINARY_URL')
    
    # 1. Intentar configurar con la URL completa (Prioridad Fly.io)
    if cloudinary_url:
        try:
            # FORZAMOS la configuración pasando la URL explícitamente
            cloudinary.config(cloudinary_url=cloudinary_url)
            app.logger.info("Cloudinary: Configurado explícitamente usando CLOUDINARY_URL.")
        except Exception as e:
            app.logger.error(f"Cloudinary: Error al configurar con URL: {e}")

    # 2. Si no hay URL, intentar con credenciales individuales (Legacy/Local)
    elif (os.environ.get('CLOUDINARY_CLOUD_NAME') and 
          os.environ.get('CLOUDINARY_API_KEY') and 
          os.environ.get('CLOUDINARY_API_SECRET')):
        
        cloudinary.config(
            cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
            api_key=os.environ.get('CLOUDINARY_API_KEY'),
            api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
            secure=True
        )
        app.logger.info("Cloudinary: Configurado usando credenciales individuales.")
    
    else:
        app.logger.warning("CLOUDINARY: ¡No se encontraron credenciales! La subida fallará.")

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
    

    @app.context_processor
    def utility_processor():
        return dict(get_transformed_profile_image_url=get_transformed_profile_image_url)

    # --- 2. INICIALIZAR EXTENSIONES ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from .models import Usuario 
    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))
    
    login_manager.login_view = 'main.login'
    login_manager.login_message = "Por favor, inicia sesión."
    login_manager.login_message_category = "warning"

    app.jinja_env.globals['get_attr'] = get_attr_safe
    app.jinja_env.add_extension('jinja2.ext.do')
    app.jinja_env.filters['tojson'] = json_dumps 

    # --- 3. REGISTRAR BLUEPRINTS ---
    with app.app_context(): 
        from .routes.main import main_bp
        from .routes.pacientes import pacientes_bp
        from .routes.pacientes_evoluciones import evoluciones_bp
        from .routes.pacientes_ajax import ajax_bp
        from .routes.pacientes_citas import citas_paciente_bp 
        from .routes.calendario import calendario_bp
        from .routes.export import export_bp
        from .routes.papelera import papelera_bp
        from .routes.planes import planes_bp



        app.register_blueprint(main_bp)
        app.register_blueprint(pacientes_bp)
        app.register_blueprint(evoluciones_bp)
        app.register_blueprint(ajax_bp)
        app.register_blueprint(citas_paciente_bp)
        app.register_blueprint(calendario_bp, url_prefix='/calendario')
        app.register_blueprint(export_bp, url_prefix='/export')
        app.register_blueprint(papelera_bp, url_prefix='/papelera')
        app.register_blueprint(planes_bp)


        @app.route('/awake')
        def awake():
            return "Render App Awake", 200
        
    return app

app = create_app()