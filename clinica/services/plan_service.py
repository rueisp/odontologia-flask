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
        from datetime import datetime
        import pytz
        from clinica.models import Usuario # Asegúrate de importar Usuario
        
        colombia_tz = pytz.timezone('America/Bogota')
        fecha_hoy = datetime.now(colombia_tz).date()
        
        # 1. Obtener datos del usuario
        user = Usuario.query.get(usuario_id)
        if not user:
            return None

        plan_info = PlanService.obtener_plan_actual_usuario(usuario_id)
        
        # 2. Si NO es admin y no tiene plan, no devolvemos nada
        if not plan_info and not user.is_admin:
            return None
        
        # Si es admin pero no tiene registro de plan (puede pasar), 
        # le asignamos valores por defecto para que no falle el dashboard
        if not plan_info:
            nombre_plan = "Administrador"
            es_trial = False
            fecha_fin = None
            dias_restantes = 999
        else:
            nombre_plan = plan_info['plan'].nombre
            es_trial = plan_info['es_trial']
            fecha_fin = plan_info['fecha_fin']
            # Calculamos días restantes reales
            f_fin = fecha_fin.date() if hasattr(fecha_fin, 'date') else fecha_fin
            dias_restantes = (f_fin - fecha_hoy).days

        # 3. Obtener límite diario (uso de hoy)
        limite_info = PlanService.verificar_limite_diario(usuario_id, fecha_hoy)
        limite_diario = limite_info.get('limite_diario')
        
        # --- Lógica de Alerta de Expiración ---
        alerta = {
            'mostrar': False,
            'clase': '',
            'mensaje': '',
            'icono': ''
        }

        # 🔥 LA CLAVE: Si es Admin, NUNCA mostramos la alerta de expiración
        if not user.is_admin:
            if dias_restantes <= 0:
                alerta = {
                    'mostrar': True,
                    'clase': 'bg-red-600',
                    'mensaje': 'Tu plan ha expirado. Estás en modo "Solo Lectura".',
                    'icono': 'alert-circle'
                }
            elif dias_restantes <= 3:
                alerta = {
                    'mostrar': True,
                    'clase': 'bg-yellow-500',
                    'mensaje': f'Tu acceso vence en {dias_restantes} días. Renueva ahora para evitar bloqueos.',
                    'icono': 'clock'
                }

# ... lógica anterior ...
        return {
            'plan_actual': nombre_plan,
            'es_trial': es_trial,
            'ya_uso_trial': PlanService.ya_uso_trial(usuario_id),
            # 🔥 CAMBIO: Enviamos 9999 en lugar de "Ilimitado" para evitar errores de comparación
            'dias_restantes': 9999 if user.is_admin else dias_restantes,
            'pacientes_hoy': limite_diario.contador_pacientes if limite_diario else 0,
            # 🔥 CAMBIO: Enviamos 9999 en lugar de "∞"
            'limite_hoy': 9999 if user.is_admin else (limite_diario.limite_actual if limite_diario else 10),
            'fecha_fin_plan': fecha_fin,
            'alerta_expiracion': alerta 
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
    
    @staticmethod
    def activar_plan(usuario_id, plan_id):
        """
        Activa un plan para un usuario (usualmente tras verificar pago manual).
        Establece 30 días de vigencia a partir de hoy.
        """
        from clinica.models import UsuarioPlan, Plan
        from clinica import db
        from datetime import datetime, timedelta
        import pytz

        colombia_tz = pytz.timezone('America/Bogota')
        ahora = datetime.now(colombia_tz)

        # 1. Desactivar cualquier plan anterior que esté 'activo' o 'trial'
        UsuarioPlan.query.filter_by(usuario_id=usuario_id, estado='activo').update({'estado': 'expirado'})
        
        # 2. Obtener datos del nuevo plan
        plan = Plan.query.get(plan_id)
        if not plan:
            return False, "Plan no encontrado"

        # 3. Crear el nuevo registro de UsuarioPlan
        # Si es el plan 'trial', son 7 días. Si es 'basico' o 'pro', son 30 días.
        dias_vigencia = 7 if plan.nombre == 'trial' else 30
        
        nuevo_usuario_plan = UsuarioPlan(
            usuario_id=usuario_id,
            plan_id=plan_id,
            estado='activo',
            es_trial=(plan.nombre == 'trial'),
            fecha_inicio=ahora,
            fecha_fin=ahora + timedelta(days=dias_vigencia)
        )

        try:
            db.session.add(nuevo_usuario_plan)
            db.session.commit()
            return True, f"Plan {plan.nombre} activado por {dias_vigencia} días."
        except Exception as e:
            db.session.rollback()
            return False, f"Error al activar el plan: {str(e)}"
        

    @staticmethod
    def ya_uso_trial(usuario_id):
        """Revisa en el historial si el usuario ya tuvo un plan trial"""
        from clinica.models import UsuarioPlan
        # Buscamos cualquier registro que sea trial, sin importar si está activo o expirado
        registro = UsuarioPlan.query.filter_by(
            usuario_id=usuario_id, 
            es_trial=True
        ).first()
        return registro is not None   