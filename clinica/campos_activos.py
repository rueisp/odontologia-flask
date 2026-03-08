"""
campos_activos.py - Definición centralizada de campos activos para consultas optimizadas

PROPÓSITO:
    Este archivo actúa como "lista blanca" de campos que se cargan desde la BD.
    Cualquier campo NO incluido aquí NO se cargará en las consultas principales,
    mejorando significativamente el rendimiento.

ESTRATEGIA DE OPTIMIZACIÓN:
    - Listados y vistas principales: usan estos campos vía load_only()
    - Operaciones de escritura (crear/editar): guardan TODOS los campos
    - Consultas específicas: pueden definir sus propios load_only si requieren más datos

MANTENIMIENTO:
    Al agregar un nuevo campo a la tabla Paciente/Evolucion:
    1. PREGUNTA: ¿Se necesita en vistas principales, listados o exports?
    2. Si SÍ → Agrégalo a la lista correspondiente
    3. Si NO → No lo agregues, úsalo con consultas específicas
"""

from sqlalchemy.orm import load_only
from clinica.models import Paciente, Evolucion

# ============================================================
# PACIENTE - Campos usados en templates y consultas principales
# ============================================================
# Estos campos se cargan en:
#   - listar_pacientes_service() 
#   - obtener_paciente_service()
#   - export.py (versión simplificada)
#   - Búsquedas y filtros principales
# ============================================================

CAMPOS_PACIENTE_ACTIVOS = [
    # --- IDENTIFICACIÓN (SIEMPRE REQUERIDOS) ---
    'id',                       # Clave primaria, indispensable
    'primer_nombre',            # Nombre principal del paciente
    'segundo_nombre',           # Se mantiene por compatibilidad (oculto en UI)
    'primer_apellido',          # Apellido principal
    'segundo_apellido',         # Se mantiene por compatibilidad (oculto en UI)
    'tipo_documento',           # CC, TI, CE, etc.
    'documento',                # Número de identificación
    
    # --- DATOS DEMOGRÁFICOS ---
    'fecha_nacimiento',         # Para cálculos de edad y demografía
    'edad',                     # Cache de edad calculada
    'telefono',                 # Contacto principal
    'email',                    # Contacto secundario
    'direccion',                # Ubicación residencial
    'barrio',                   # Segmentación geográfica
    
    # --- INFORMACIÓN CLÍNICA SIMPLIFICADA ---
    'alergias',                 # Alertas médicas (sección Clínica Simple)
    'motivo_consulta',          # Razón de visita actual
    'enfermedad_actual',        # Descripción del problema actual
    'observaciones',            # Notas generales adicionales
    
    # --- MULTIMEDIA Y RELACIONES ---
    'imagen_perfil_url',        # Foto del paciente (avatar)
    'dentigrama_canvas',        # Datos del odontograma (formato JSON)
    'odontologo_id',            # FK al odontólogo asignado
    
    # --- CONTROL Y ESTADO ---
    'is_deleted',               # Flag para soft delete
    
    # --- CAMPOS CALCULADOS (PROPERTIES) ---
    'nombres',      # Property: primer_nombre + segundo_nombre (compatibilidad)
    'apellidos'     # Property: primer_apellido + segundo_apellido (compatibilidad)
]

def load_only_paciente_activo():
    """
    Retorna configuración load_only para consultas de Paciente
    
    Uso:
        pacientes = db.session.query(Paciente).options(
            load_only_paciente_activo()
        ).all()
    
    Returns:
        load_only object con los campos activos de Paciente
    """
    return load_only(*[getattr(Paciente, campo) for campo in CAMPOS_PACIENTE_ACTIVOS])

# ============================================================
# EVOLUCION - Campos usados en templates
# ============================================================
# Nota: Las evoluciones se cargan por separado en la vista de perfil
# para evitar el joinedload que traía todos los datos del paciente
# ============================================================

CAMPOS_EVOLUCION_ACTIVOS = [
    'id',               # Clave primaria
    'descripcion',      # Contenido de la evolución (texto)
    'fecha',            # Fecha de creación/modificación
    'paciente_id'       # FK para relaciones (no se carga el objeto Paciente completo)
]

def load_only_evolucion_activo():
    """
    Retorna configuración load_only para consultas de Evolucion
    
    Uso:
        evoluciones = db.session.query(Evolucion).options(
            load_only_evolucion_activo()
        ).filter_by(paciente_id=id).all()
    
    Returns:
        load_only object con los campos activos de Evolucion
    """
    return load_only(*[getattr(Evolucion, campo) for campo in CAMPOS_EVOLUCION_ACTIVOS])

# ============================================================
# NOTAS PARA DESARROLLADORES
# ============================================================
"""
CAMBIOS RECIENTES (Refactorización Marzo 2026):
    - Eliminados: genero, estado_civil, ocupacion, datos_responsable
    - Eliminados: antecedentes_personales, antecedentes_familiares, imagenes_adicionales
    - Agregados: alergias, motivo_consulta, enfermedad_actual, observaciones
    - Optimizado: Las evoluciones ya no cargan el paciente completo

VALIDACIÓN DE CAMPOS:
    Si un campo falta en estas listas y se intenta acceder en un template,
    lanzará error. Siempre verificar que los campos mostrados en UI estén aquí.

CONTACTO PARA DUDAS:
    - Sistema: Sistema Odontológico Simplificado
    - Rama principal: version-simple
"""