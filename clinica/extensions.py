# extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_caching import Cache

# Crea las instancias de las extensiones SIN inicializarlas con una app
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
cache = Cache()  # 👈 Agregar esta línea


# Configura el login_manager aquí, ya que no depende de la app
login_manager.login_view = 'main.login' # ¡OJO! Cambiaremos 'login' a 'auth.login'
login_manager.login_message = "Por favor, inicia sesión para acceder a esta página."
login_manager.login_message_category = "info"
