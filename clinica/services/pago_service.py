# clinica/services/pago_service.py

# Asegúrate de que las siguientes líneas de importación sean correctas para tu proyecto
from clinica.models import SolicitudPago, Plan  
from clinica.extensions import db 

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
            
        # ************************************************
        # ** ESTA ES LA ÚNICA LÍNEA QUE DEBES CAMBIAR **
        # ************************************************
        # ANTES: monto_cop = int(plan.precio_mensual)
        # AHORA: Usa el campo que contiene el valor correcto (20000)
        monto_cop = plan.precio_cop
        # ************************************************
        
        # 2. Crear el nuevo objeto de SolicitudPago
        nueva_solicitud = SolicitudPago(
            user_id=user_id,
            plan_id=plan_id,
            plan_nombre=plan.nombre, # Usar el nombre del Plan de la DB
            monto_cop=monto_cop,     # <-- Ahora vale 20000 o 28000
            estado='PENDIENTE',
        )

        # 3. Guardar en la base de datos (con manejo de errores)
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
        # Consulta el modelo real en la DB
        return SolicitudPago.query.get(solicitud_id)