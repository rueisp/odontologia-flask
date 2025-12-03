# clinica/services/plan_service.py

from datetime import datetime, timedelta
from clinica import db
from clinica.models import Plan, Usuario, UsuarioPlan, LimiteDiario

class PlanService:
    """Servicio para manejar lógica de planes y suscripciones"""
    
    @staticmethod
    def inicializar_planes():
        """Crear planes iniciales si no existen"""
        planes_a_crear = [
            {
                'nombre': 'trial',
                'descripcion': 'Plan de prueba de 30 días',
                'precio_mensual': 0.0,
                'limite_pacientes_diario': 10,
                'limite_pacientes_diario_primeros_7_dias': 20,
                'duracion_trial_dias': 30,
                'caracteristicas': {
                    'features': [
                        '30 días completos',
                        '20 pacientes/día primeros 7 días',
                        '10 pacientes/día después',
                        'Acceso completo',
                        'Soporte básico'
                    ]
                },
                'activo': True,
                'orden': 1
            },
            {
                'nombre': 'basico',
                'descripcion': 'Plan básico para práctica pequeña',
                'precio_mensual': 7.0,
                'limite_pacientes_diario': 25,
                'limite_pacientes_diario_primeros_7_dias': 25,
                'duracion_trial_dias': 0,
                'caracteristicas': {
                    'features': [
                        '25 pacientes/día',
                        'Historial completo',
                        'Facturación electrónica',
                        'Backup automático',
                        'Soporte prioritario'
                    ]
                },
                'activo': True,
                'orden': 2
            },
            {
                'nombre': 'profesional',
                'descripcion': 'Plan profesional para clínicas',
                'precio_mensual': 15.0,
                'limite_pacientes_diario': 50,
                'limite_pacientes_diario_primeros_7_dias': 50,
                'duracion_trial_dias': 0,
                'caracteristicas': {
                    'features': [
                        '50 pacientes/día',
                        'Múltiples usuarios',
                        'Reportes avanzados',
                        'Integración RIPS completa',
                        'Soporte 24/7'
                    ]
                },
                'activo': True,
                'orden': 3
            }
        ]
        
        for plan_data in planes_a_crear:
            plan_existente = Plan.query.filter_by(nombre=plan_data['nombre']).first()
            if not plan_existente:
                nuevo_plan = Plan(**plan_data)
                db.session.add(nuevo_plan)
                print(f"Plan '{plan_data['nombre']}' creado.")
        
        db.session.commit()
        print("Planes inicializados correctamente.")
    
    @staticmethod
    def asignar_trial_a_usuarios():
        """Asignar plan trial a todos los usuarios que no tengan plan"""
        plan_trial = Plan.query.filter_by(nombre='trial').first()
        
        if not plan_trial:
            print("Error: Plan trial no encontrado.")
            return
        
        usuarios_sin_plan = Usuario.query.filter(
            ~Usuario.planes.any(UsuarioPlan.estado.in_(['activo', 'trial']))
        ).all()
        
        for usuario in usuarios_sin_plan:
            # Verificar si ya tiene un plan trial activo
            plan_trial_activo = UsuarioPlan.query.filter_by(
                usuario_id=usuario.id,
                plan_id=plan_trial.id,
                estado='activo'
            ).first()
            
            if not plan_trial_activo:
                nuevo_usuario_plan = UsuarioPlan(
                    usuario_id=usuario.id,
                    plan_id=plan_trial.id,
                    estado='activo',
                    es_trial=True,
                    trial_dias_restantes=30,
                    trial_pacientes_primeros_7_dias=True,
                    fecha_inicio=datetime.utcnow(),
                    fecha_fin=datetime.utcnow() + timedelta(days=30)
                )
                db.session.add(nuevo_usuario_plan)
                print(f"Trial asignado a usuario: {usuario.email}")
        
        db.session.commit()
        print("Trial asignado a usuarios existentes.")
    
    @staticmethod
    def obtener_plan_actual_usuario(usuario_id):
        """Obtener el plan actual activo de un usuario"""
        usuario_plan = UsuarioPlan.query.filter_by(
            usuario_id=usuario_id,
            estado='activo'
        ).order_by(UsuarioPlan.fecha_inicio.desc()).first()
        
        if usuario_plan:
            return {
                'plan': usuario_plan.plan,
                'usuario_plan': usuario_plan,
                'es_trial': usuario_plan.es_trial,
                'dias_restantes': usuario_plan.trial_dias_restantes if usuario_plan.es_trial else None,
                'fecha_fin': usuario_plan.fecha_fin
            }
        return None
    
    @staticmethod
    def verificar_limite_diario(usuario_id, fecha=None):
        """Verificar y actualizar límite diario para un usuario"""
        if fecha is None:
            fecha = datetime.utcnow().date()
        
        # Obtener plan actual
        plan_info = PlanService.obtener_plan_actual_usuario(usuario_id)
        if not plan_info:
            return {'error': 'Usuario sin plan activo'}
        
        plan = plan_info['plan']
        usuario_plan = plan_info['usuario_plan']
        
        # Obtener o crear límite diario
        limite_diario = LimiteDiario.query.filter_by(
            usuario_id=usuario_id,
            fecha=fecha
        ).first()
        
        if not limite_diario:
            # Calcular límite según día del trial
            limite_actual = plan.limite_pacientes_diario
            
            if usuario_plan.es_trial and usuario_plan.trial_pacientes_primeros_7_dias:
                # Calcular días desde inicio del trial
                dias_desde_inicio = (fecha - usuario_plan.fecha_inicio.date()).days
                if dias_desde_inicio < 7:
                    limite_actual = plan.limite_pacientes_diario_primeros_7_dias
            
            limite_diario = LimiteDiario(
                usuario_id=usuario_id,
                fecha=fecha,
                limite_actual=limite_actual,
                es_dia_trial=usuario_plan.es_trial,
                dia_numero_trial=(fecha - usuario_plan.fecha_inicio.date()).days + 1 if usuario_plan.es_trial else None
            )
            db.session.add(limite_diario)
            db.session.commit()
        
        return {
            'limite_diario': limite_diario,
            'plan': plan,
            'usuario_plan': usuario_plan,
            'puede_crear': limite_diario.contador_pacientes < limite_diario.limite_actual
        }
    
    @staticmethod
    def incrementar_contador_paciente(usuario_id):
        """Incrementar contador de pacientes creados hoy"""
        fecha_hoy = datetime.utcnow().date()
        
        # Verificar límite primero
        verificacion = PlanService.verificar_limite_diario(usuario_id, fecha_hoy)
        if 'error' in verificacion:
            return verificacion
        
        limite_diario = verificacion['limite_diario']
        
        # Verificar si puede crear más pacientes
        if limite_diario.contador_pacientes >= limite_diario.limite_actual:
            return {
                'exito': False,
                'error': 'Límite diario alcanzado',
                'limite_diario': limite_diario
            }
        
        # Incrementar contador
        limite_diario.contador_pacientes += 1
        db.session.commit()
        
        return {
            'exito': True,
            'limite_diario': limite_diario,
            'restantes': limite_diario.limite_actual - limite_diario.contador_pacientes
        }
    

    @staticmethod
    def obtener_estadisticas_usuario(usuario_id):
        """Obtener estadísticas del usuario para mostrar en dashboard"""
        from datetime import datetime
        
        fecha_hoy = datetime.utcnow().date()
        
        # Obtener plan actual
        plan_info = PlanService.obtener_plan_actual_usuario(usuario_id)
        if not plan_info:
            return None
        
        # Obtener límite diario
        limite_info = PlanService.verificar_limite_diario(usuario_id, fecha_hoy)
        if 'error' in limite_info:
            return None
        
        limite_diario = limite_info['limite_diario']
        
        # Calcular días restantes de trial
        dias_restantes = None
        if plan_info['es_trial'] and plan_info['fecha_fin']:
            dias_restantes = (plan_info['fecha_fin'].date() - fecha_hoy).days
            dias_restantes = max(0, dias_restantes)  # No negativo
        
        return {
            'plan_actual': plan_info['plan'].nombre,
            'es_trial': plan_info['es_trial'],
            'dias_restantes_trial': dias_restantes,
            'pacientes_hoy': limite_diario.contador_pacientes,
            'limite_hoy': limite_diario.limite_actual,
            'dia_trial_actual': limite_diario.dia_numero_trial if limite_diario.es_dia_trial else None,
            'fecha_fin_plan': plan_info['fecha_fin'],
            'limite_alcanzado': limite_diario.contador_pacientes >= limite_diario.limite_actual
        }