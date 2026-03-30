from flask import Blueprint

# Definimos el Blueprint UNIFICADO para todo lo relacionado con pacientes
pacientes_bp = Blueprint('pacientes', __name__, url_prefix='/pacientes')

# Importamos las rutas de los otros archivos para que se registren en el blueprint
from . import principal
from . import evoluciones
from . import consultas_ajax