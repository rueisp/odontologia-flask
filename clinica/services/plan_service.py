# clinica/services/plan_service.py

from datetime import datetime, timedelta, date
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
                'descripcion': 'Plan de prueba de 7 días',
                'precio_mensual': 0.0,
                'limite_pacientes_diario': 10,
                'limite_pacientes_diario_primeros_7_dias': 70,
                'duracion_trial_dias': 7,
                'caracteristicas': {
                    'features': [
                        '10 pacientes por día',
                        'Hasta 70 pacientes en total (7 días)',
                        'Acceso completo al sistema'
                    ]
                },
                'activo': True,
                'orden': 1
            },
            {
                'nombre': 'basico',
                'descripcion': 'Plan básico para odontólogos independientes',
                'precio_mensual': 20000.0,  # 🔹 Cambiado de 20000 a 20000.0 por claridad
                'limite_pacientes_diario': 20,
                'limite_pacientes_diario_primeros_7_dias': 20,
                'duracion_trial_dias': 0,
                'caracteristicas': {
                    'features': [
                        '20 pacientes por día',
                        'Hasta 1.000 pacientes registrados',
                        'Historial clínico completo',
                        'Acceso completo al sistema'
                    ]
                },
                'activo': True,
                'orden': 2
            },
            {
                'nombre': 'pro',  # 🔹 Cambiado de 'profesional' a 'pro'
                'descripcion': 'Plan profesional para clínicas pequeñas',
                'precio_mensual': 30000.0,  # 🔹 Cambiado de 30000 a 30000.0
                'limite_pacientes_diario': 50,
                'limite_pacientes_diario_primeros_7_dias': 50,
                'duracion_trial_dias': 0,
                'caracteristicas': {
                    'features': [
                        '50 pacientes por día',
                        'Hasta 3.000 pacientes registrados',
                        'Historial clínico completo',
                        'Acceso completo al sistema'
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
                    trial_dias_restantes=7,
                    trial_pacientes_primeros_7_dias=True,
                    fecha_inicio=datetime.utcnow(),
                    fecha_fin=datetime.utcnow() + timedelta(days=7)
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
        from clinica.models import LimiteDiario, UsuarioPlan, Plan
        from clinica import db
        from datetime import date
        
        if fecha is None:
            fecha = date.today()
        
        # Buscar límite diario existente
        limite_diario = LimiteDiario.query.filter_by(
            usuario_id=usuario_id, 
            fecha=fecha
        ).first()
        
        # Si no existe, crearlo
        if limite_diario is None:
            # Obtener el plan activo del usuario
            usuario_plan = UsuarioPlan.query.filter_by(
                usuario_id=usuario_id,
                estado='activo'
            ).first()
            
            if usuario_plan:
                plan = Plan.query.get(usuario_plan.plan_id)
                limite_actual = plan.limite_pacientes_diario if plan else 10
                es_trial = usuario_plan.es_trial
            else:
                # Si no tiene plan, usar límite por defecto (10)
                limite_actual = 10
                es_trial = False
            
            # Crear nuevo registro de límite diario
            limite_diario = LimiteDiario(
                usuario_id=usuario_id,
                fecha=fecha,
                contador_pacientes=0,
                limite_actual=limite_actual,
                es_dia_trial=es_trial
            )
            db.session.add(limite_diario)
            db.session.commit()
        
        # Devolver diccionario con los datos necesarios
        return {
            'limite_diario': limite_diario,
            'puede_crear': limite_diario.contador_pacientes < limite_diario.limite_actual,
            'contador': limite_diario.contador_pacientes,
            'limite': limite_diario.limite_actual,
            'limite_restante': limite_diario.limite_actual - limite_diario.contador_pacientes
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
        import pytz
        
        # Usar zona horaria de Colombia
        colombia_tz = pytz.timezone('America/Bogota')
        fecha_hoy = datetime.now(colombia_tz).date()
        
        # Obtener plan actual
        plan_info = PlanService.obtener_plan_actual_usuario(usuario_id)
        if not plan_info:
            return None
        
        # Obtener límite diario
        limite_info = PlanService.verificar_limite_diario(usuario_id, fecha_hoy)
        
        # Verificar si hay error en el límite
        if not limite_info or 'error' in limite_info:
            # Si hay error, devolver estadísticas básicas sin límite
            return {
                'plan_actual': plan_info['plan'].nombre,
                'es_trial': plan_info['es_trial'],
                'dias_restantes_trial': None,
                'pacientes_hoy': 0,
                'limite_hoy': plan_info['plan'].limite_pacientes_diario if plan_info['plan'] else 10,
                'dia_trial_actual': None,
                'fecha_fin_plan': plan_info['fecha_fin'],
                'limite_alcanzado': False
            }
        
        # Obtener el objeto limite_diario
        limite_diario = limite_info.get('limite_diario')
        
        # Si no hay limite_diario, crear uno básico
        if not limite_diario:
            return {
                'plan_actual': plan_info['plan'].nombre,
                'es_trial': plan_info['es_trial'],
                'dias_restantes_trial': None,
                'pacientes_hoy': 0,
                'limite_hoy': plan_info['plan'].limite_pacientes_diario if plan_info['plan'] else 10,
                'dia_trial_actual': None,
                'fecha_fin_plan': plan_info['fecha_fin'],
                'limite_alcanzado': False
            }
        
        # Calcular días restantes de trial
        dias_restantes = None
        if plan_info['es_trial'] and plan_info['fecha_fin']:
            dias_restantes = (plan_info['fecha_fin'].date() - fecha_hoy).days
            dias_restantes = max(0, dias_restantes)  # No negativo
        
        return {
            'plan_actual': plan_info['plan'].nombre,
            'es_trial': plan_info['es_trial'],
            'dias_restantes_trial': dias_restantes,
            'pacientes_hoy': limite_diario.contador_pacientes if hasattr(limite_diario, 'contador_pacientes') else 0,
            'limite_hoy': limite_diario.limite_actual if hasattr(limite_diario, 'limite_actual') else 10,
            'dia_trial_actual': limite_diario.dia_numero_trial if hasattr(limite_diario, 'dia_numero_trial') and limite_diario.es_dia_trial else None,
            'fecha_fin_plan': plan_info['fecha_fin'],
            'limite_alcanzado': (limite_diario.contador_pacientes >= limite_diario.limite_actual) if hasattr(limite_diario, 'contador_pacientes') and hasattr(limite_diario, 'limite_actual') else False
        }
    
    @staticmethod
    def verificar_expiraciones():
        """Verificar y desactivar planes expirados"""
        ahora = datetime.utcnow()
        
        # Buscar planes activos con fecha_fin pasada
        expirados = UsuarioPlan.query.filter(
            UsuarioPlan.estado == 'activo',
            UsuarioPlan.fecha_fin < ahora
        ).all()
        
        for usuario_plan in expirados:
            usuario_plan.estado = 'expirado'
            print(f"Plan {usuario_plan.plan.nombre} expirado para usuario {usuario_plan.usuario_id}")
        
        db.session.commit()
        return len(expirados)