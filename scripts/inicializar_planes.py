# scripts/inicializar_planes.py

import sys
import os

# Agregar la raíz del proyecto al path para poder importar
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clinica import create_app, db
from clinica.services.plan_service import PlanService

app = create_app()

with app.app_context():
    print("=== INICIALIZANDO SISTEMA DE PLANES ===")
    
    # 1. Crear planes
    PlanService.inicializar_planes()
    
    # 2. Asignar trial a usuarios existentes
    PlanService.asignar_trial_a_usuarios()
    
    print("=== SISTEMA DE PLANES INICIALIZADO ===")
    print("✓ Planes creados: trial, básico, profesional")
    print("✓ Trial asignado a usuarios existentes")