from flask import Blueprint

calendario_bp = Blueprint('calendario', __name__, url_prefix='/calendario')

from . import routes
from . import disponibilidad
from . import citas