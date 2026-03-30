import os
from flask import Flask, request
from .extensions import db, migrate, login_manager 
import cloudinary
from dotenv import load_dotenv
import logging
from flask.json import dumps as json_dumps
from .utils import get_transformed_profile_image_url

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

# --- 1. IMPORTAR BLUEPRINTS ---
# Nota cómo ahora solo importamos UNO de pacientes, 
# porque ese ya contiene a los demás (evoluciones, ajax, etc.)
from .routes.main import main_bp
from .routes.pacientes import pacientes_bp  # <--- Este ahora es el unificado
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

    # ... (el resto de tu lógica de logging y cloudinary se mantiene igual) ...

    # --- 2. INICIALIZAR EXTENSIONES ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
        # 🔥 ESTO ES LO QUE FALTA: REGISTRAR FUNCIONES GLOBALES PARA EL HTML 🔥
    app.jinja_env.globals['get_transformed_profile_image_url'] = get_transformed_profile_image_url
    app.jinja_env.globals['get_attr'] = get_attr_safe
    # ----------------------------------------------------------------------

    from .models import Usuario 
    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))
    
    login_manager.login_view = 'main.login'


    # Al lado de donde registraste las funciones globales de Jinja:
    @app.context_processor
    def inject_subscription_info():
        from flask_login import current_user
        from clinica.services.plan_service import PlanService
        
        if current_user.is_authenticated:
            # Esto hace que 'estadisticas_plan' esté disponible en TODO el HTML
            stats = PlanService.obtener_estadisticas_usuario(current_user.id)
            return dict(estadisticas_plan=stats)
        return dict(estadisticas_plan=None)


    # --- 3. REGISTRAR BLUEPRINTS ---
    app.register_blueprint(main_bp)
    
    # REGISTRO UNIFICADO:
    # Al registrar este, automáticamente se registran 'principal', 'evoluciones' y 'ajax'
    # porque están dentro de la carpeta pacientes
    app.register_blueprint(pacientes_bp) 

    # Otros blueprints
    app.register_blueprint(calendario_bp, url_prefix='/calendario')
    app.register_blueprint(export_bp, url_prefix='/export')
    app.register_blueprint(papelera_bp, url_prefix='/papelera')
    app.register_blueprint(planes_bp)
    app.register_blueprint(pagos_bp)
    app.register_blueprint(admin_bp)

    return app

app = create_app()