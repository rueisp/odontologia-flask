# clinica/services/pago_service.py

from clinica.models import SolicitudPago, Plan, UsuarioPlan
from clinica.extensions import db
from datetime import datetime, timedelta

class PagoService:
    
    @staticmethod
    def registrar_solicitud_manual(user_id, plan_id, plan_nombre):
        """
        Registra la solicitud de pago manual en la DB.
        Retorna el ID de la solicitud y el monto.
        """
        # 1. Obtener el Plan de la DB para obtener el monto real
        plan = Plan.query.get(plan_id)
        if not plan:
            raise ValueError(f"Plan con ID {plan_id} no encontrado.")
            
        # 2. Usar el campo precio_cop (ya está correcto)
        monto_cop = plan.precio_cop
        
        # 3. Crear el nuevo objeto de SolicitudPago
        nueva_solicitud = SolicitudPago(
            user_id=user_id,
            plan_id=plan_id,
            plan_nombre=plan.nombre,
            monto_cop=monto_cop,
            estado='PENDIENTE',
        )

        # 4. Guardar en la base de datos
        try:
            db.session.add(nueva_solicitud)
            db.session.commit()
            return nueva_solicitud.id, monto_cop
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Error al registrar la solicitud de pago: {e}")

    @staticmethod
    def obtener_solicitud_por_id(solicitud_id):
        """
        Obtiene los datos de la solicitud de pago de la DB.
        """
        return SolicitudPago.query.get(solicitud_id)

    @staticmethod
    def verificar_pago(solicitud_id):
        """
        Marca una solicitud como VERIFICADA y activa el plan del usuario.
        """
        solicitud = SolicitudPago.query.get(solicitud_id)
        if not solicitud:
            return False, "Solicitud no encontrada"
        
        # Cambiar estado
        solicitud.estado = 'VERIFICADO'
        solicitud.fecha_verificacion = datetime.utcnow()
        
        # Activar el plan para el usuario
        from clinica.services.plan_service import PlanService
        PlanService.activar_plan(
            usuario_id=solicitud.user_id,
            plan_id=solicitud.plan_id
        )
        
        try:
            db.session.commit()
            return True, "Pago verificado y plan activado"
        except Exception as e:
            db.session.rollback()
            return False, f"Error al verificar: {e}"

    @staticmethod
    def cancelar_solicitud(solicitud_id):
        """
        Cancela una solicitud de pago pendiente.
        """
        solicitud = SolicitudPago.query.get(solicitud_id)
        if solicitud and solicitud.estado == 'PENDIENTE':
            solicitud.estado = 'CANCELADO'
            db.session.commit()
            return True
        return False