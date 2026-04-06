import os
from flask import Flask, request
from .extensions import db, migrate, login_manager, cache 
import cloudinary
from dotenv import load_dotenv
import logging
from flask.json import dumps as json_dumps
from .utils import get_transformed_profile_image_url
from flask_compress import Compress
from sqlalchemy import event

# Cargar .env
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

# --- IMPORTAR BLUEPRINTS ---
from .routes.main import main_bp
from .routes.pacientes import pacientes_bp
from .routes.calendario import calendario_bp
from .routes.export import export_bp
from .routes.papelera import papelera_bp
from .routes.planes import planes_bp
from clinica.routes.pagos import pagos_bp
from .routes.admin import admin_bp

def create_app():
 
    app = Flask(__name__, instance_relative_config=True)

    # --- CONFIGURACIÓN ---
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(24).hex()),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///instance/clinica.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        DEBUG=os.environ.get('FLASK_DEBUG') == '1'
    )



    app.config['CACHE_TYPE'] = 'SimpleCache'
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300

    app.config['COMPRESS_MIMETYPES'] = ['text/html', 'text/css', 'text/xml', 'application/json', 'application/javascript']
    app.config['COMPRESS_LEVEL'] = 6
    app.config['COMPRESS_MIN_SIZE'] = 500

    Compress(app)

    # --- INICIALIZAR EXTENSIONES ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    cache.init_app(app)
    

        # ============================================================
    # 👇 LOGGING ESTRUCTURADO - PEGA AQUÍ 👇
    # ============================================================
    if not app.debug:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)
        
        file_handler = logging.FileHandler('logs/app_errors.log')
        file_handler.setLevel(logging.ERROR)
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info("Aplicación iniciada con logging estructurado")
    # ============================================================

    # 👈 TIMEOUT PARA CONSULTAS - COMENTADO TEMPORALMENTE
    # @event.listens_for(db.engine, 'connect')
    # def set_statement_timeout(dbapi_connection, connection_record):
    #     cursor = dbapi_connection.cursor()
    #     cursor.execute('SET statement_timeout = 30000')
    #     cursor.close()

    # FUNCIONES GLOBALES PARA HTML
    app.jinja_env.globals['get_transformed_profile_image_url'] = get_transformed_profile_image_url
    app.jinja_env.globals['get_attr'] = get_attr_safe

    from .models import Usuario
    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    login_manager.login_view = 'main.login'

    @app.context_processor
    def inject_subscription_info():
        from flask_login import current_user
        from clinica.services.plan_service import PlanService

        if current_user.is_authenticated:
            stats = PlanService.obtener_estadisticas_usuario(current_user.id)
            return dict(estadisticas_plan=stats)
        return dict(estadisticas_plan=None)

    # --- REGISTRAR BLUEPRINTS ---
    app.register_blueprint(main_bp)
    app.register_blueprint(pacientes_bp)
    app.register_blueprint(calendario_bp, url_prefix='/calendario')
    app.register_blueprint(export_bp, url_prefix='/export')
    app.register_blueprint(papelera_bp, url_prefix='/papelera')
    app.register_blueprint(planes_bp)
    app.register_blueprint(pagos_bp)
    app.register_blueprint(admin_bp)

        # 👈 AL FINAL, ANTES DE `return app`
    # Verificar expiraciones al iniciar
    # from clinica.services.plan_service import PlanService
    # with app.app_context():
    #     expirados = PlanService.verificar_expiraciones()
    #     if expirados > 0:
    #         print(f"Se desactivaron {expirados} planes expirados")

    return app

app = create_app()
