# clinica/routes/facturacion.py

from flask import Blueprint, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
import pytz
# Importamos las herramientas y modelos necesarios
from ..extensions import db
from ..models import Factura, Cita, Paciente

# Creamos el Blueprint para estas rutas
facturacion_bp = Blueprint('facturacion', __name__)


@facturacion_bp.route('/paciente/<int:paciente_id>/crear-factura', methods=['POST'])
@login_required
def crear_factura_para_paciente(paciente_id):
    """
    Esta ruta crea una nueva factura y la asocia a todas las citas de un
    paciente que aún no han sido facturadas.
    """
    # 1. Buscamos al paciente para asegurarnos de que existe
    paciente = Paciente.query.get_or_404(paciente_id)

    # SEGURIDAD: Verificar que el paciente pertenezca al odontólogo actual
    if not current_user.is_admin and paciente.odontologo_id != current_user.id:
        flash('No tienes permiso para facturar a este paciente.', 'danger')
        return redirect(url_for('main.index'))
    
    # 2. Buscamos todas las citas de este paciente que NO tienen una factura asignada
    # Buscamos todas las citas de este paciente que NO tienen una factura asignada
    citas_a_facturar = Cita.query.filter_by(paciente_id=paciente_id, factura_id=None).all()

    # ▼▼▼ ¡ESTE BLOQUE ES EL MÁS IMPORTANTE! ▼▼▼
    # Verifica si hay algo que facturar ANTES de crear la factura.
    if not citas_a_facturar:
        flash('No hay citas pendientes de facturación para este paciente.', 'warning')
        return redirect(url_for('calendario.historial_citas_paciente', paciente_id=paciente_id))
    # ▲▲▲ ¡FIN DEL BLOQUE IMPORTANTE! ▲▲▲
    try:
        # 4. CALCULAR EL VALOR TOTAL (NUEVO)
        # ------------------------------------------------------------------
        # Recorremos las citas que vamos a facturar y sumamos sus procedimientos
        total_factura = 0.0
        
        for cita in citas_a_facturar:
            # 'procedimientos' es la relación que definimos en models.py
            for proc in cita.procedimientos:
                # Sumamos el valor (usamos (proc.valor or 0) por seguridad si alguno está vacío)
                total_factura += (proc.valor or 0.0)
        # ------------------------------------------------------------------

        # Generamos un número de factura único.
        numero_factura_generado = f"FACT-{paciente.id}-{int(datetime.now().timestamp())}"

        nueva_factura = Factura(
            numero_factura=numero_factura_generado,
            fecha_factura=datetime.now(pytz.utc),
            paciente_id=paciente.id,
            valor_total=total_factura  # <--- ¡AQUÍ ASIGNAMOS LA SUMA REAL!
        )

        # 5. Guardamos la nueva factura en la base de datos PRIMERO
        db.session.add(nueva_factura)
        db.session.commit()

        # 6. Ahora que 'nueva_factura' tiene un 'id', lo asignamos a cada cita pendiente
        for cita in citas_a_facturar:
            cita.factura_id = nueva_factura.id
        
        # 7. Guardamos los cambios en las citas
        db.session.commit()

        # Mensaje de éxito mostrando el valor formateado (ej: $50,000)
        flash(f'Factura {nueva_factura.numero_factura} creada por valor de ${total_factura:,.0f}', 'success')

    except Exception as e:
        db.session.rollback() # Si algo falla, deshacemos los cambios
        flash(f'Error al crear la factura: {e}', 'danger')

    # 8. Al final, redirigimos al usuario a la misma página de historial de citas
    return redirect(url_for('calendario.historial_citas_paciente', paciente_id=paciente_id))