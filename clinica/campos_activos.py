"""
Definición centralizada de los campos que realmente se usan en la UI.
"""
from sqlalchemy.orm import load_only
from clinica.models import Paciente, Evolucion

# ============================================================
# PACIENTE - Campos usados en templates
# ============================================================
CAMPOS_PACIENTE_ACTIVOS = [
    'id',
    'primer_nombre',
    'segundo_nombre',
    'primer_apellido',
    'segundo_apellido',
    'tipo_documento',
    'documento',
    'fecha_nacimiento',
    'edad',
    'telefono',
    'email',
    'direccion',
    'barrio',
    'alergias',
    'enfermedades_importantes',
    'observaciones_generales',
    'imagen_perfil_url',
    'dentigrama_canvas',
    'odontologo_id',
    'is_deleted'
]

def load_only_paciente_activo():
    """Retorna configuración load_only para consultas de Paciente"""
    return load_only(*[getattr(Paciente, campo) for campo in CAMPOS_PACIENTE_ACTIVOS])

# ============================================================
# EVOLUCION - Campos usados en templates
# ============================================================
CAMPOS_EVOLUCION_ACTIVOS = [
    'id',
    'descripcion',
    'fecha',
    'paciente_id'
]

def load_only_evolucion_activo():
    """Retorna configuración load_only para consultas de Evolucion"""
    return load_only(*[getattr(Evolucion, campo) for campo in CAMPOS_EVOLUCION_ACTIVOS])