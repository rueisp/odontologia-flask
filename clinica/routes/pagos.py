# routes/pagos.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import date, datetime
from clinica.models import db, PagoUnificado
import random
import string

pagos_bp = Blueprint('pagos', __name__, url_prefix='/pagos')

def generar_codigo_unico():
    """Genera un código único para el recibo"""
    fecha_str = date.today().strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"R-{fecha_str}-{random_str}"

# ============================================================
# RUTA PARA NUEVO PAGO (COBRO RÁPIDO)
# ============================================================
@pagos_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_pago():
    """Vista para cobro rápido con autocompletado de pacientes"""
    from clinica.models import Paciente
    
    if request.method == 'POST':
        try:
            # Procesar el formulario
            fecha = datetime.strptime(request.form.get('fecha'), '%Y-%m-%d').date()
            hora = datetime.now().time()
            descripcion = request.form.get('descripcion')
            monto = int(request.form.get('monto', 0))
            metodo_pago = request.form.get('metodo_pago')
            observacion = request.form.get('observacion')
            pagado_por = request.form.get('pagado_por')
            
            # Obtener datos del paciente
            paciente_id = request.form.get('paciente_id', type=int)
            paciente_nombre = request.form.get('paciente_nombre')
            
            # Si viene paciente_id, verificar que existe
            if paciente_id:
                paciente = Paciente.query.get(paciente_id)
                if paciente:
                    paciente_nombre = f"{paciente.primer_nombre} {paciente.primer_apellido}"
                    es_rapido = False
                    flash(f'✅ Pago vinculado al paciente {paciente_nombre}', 'success')
                else:
                    paciente_id = None
                    es_rapido = True
            else:
                es_rapido = True
            
            # Crear el pago
            nuevo_pago = PagoUnificado(
                paciente_id=paciente_id,
                paciente_nombre=paciente_nombre,
                fecha=fecha,
                hora=hora,
                descripcion=descripcion,
                monto=monto,
                metodo_pago=metodo_pago,
                observacion=observacion,
                pagado_por=pagado_por,
                codigo=generar_codigo_unico(),
                es_rapido=es_rapido,
                usuario_id=current_user.id
            )
            
            db.session.add(nuevo_pago)
            db.session.commit()
            
            return redirect(url_for('pagos.ver_pago', pago_id=nuevo_pago.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar el pago: {str(e)}', 'danger')
            return redirect(url_for('pagos.nuevo_pago'))
    
    # GET - Mostrar formulario
    today = date.today().isoformat()
    return render_template('pagos/rapido.html', today=today)


# ============================================================
# RUTA PARA VER DETALLE DEL PAGO
# ============================================================

@pagos_bp.route('/<int:pago_id>')
@login_required
def ver_pago(pago_id):
    """Muestra el detalle de un pago y prepara el enlace de WhatsApp"""
    from clinica.models import PagoUnificado, Paciente
    import urllib.parse
    
    pago = PagoUnificado.query.get_or_404(pago_id)
    
    # Verificar permisos
    if pago.usuario_id != current_user.id and not current_user.is_admin:
        flash('No tienes permiso para ver este pago', 'danger')
        return redirect(url_for('main.index'))
    
    # Variables para WhatsApp
    telefono = None
    whatsapp_link = None
    tiene_telefono = False
    
    # Si el pago tiene paciente_id, buscamos su teléfono
    if pago.paciente_id:
        paciente = Paciente.query.get(pago.paciente_id)
        if paciente and paciente.telefono:
            telefono = paciente.telefono
            tiene_telefono = True
            
            # Crear el mensaje
            mensaje = f"""*🧾 RECIBO DE PAGO - CLÍNICA DENTAL*

*Código:* {pago.codigo}
*Paciente:* {pago.paciente_nombre}
*Fecha:* {pago.fecha.strftime('%d/%m/%Y')} {pago.hora.strftime('%H:%M')}
*Descripción:* {pago.descripcion}
*Monto:* ${'{:,.0f}'.format(pago.monto)}
*Método:* {pago.metodo_pago}"""

            if pago.pagado_por:
                mensaje += f"\n*Pagado por:* {pago.pagado_por}"
            if pago.observacion:
                mensaje += f"\n*Observación:* {pago.observacion}"
            
            # Codificar el mensaje para la URL
            mensaje_codificado = urllib.parse.quote(mensaje)
            
            # Crear el enlace de WhatsApp
            # Limpiar el teléfono: eliminar espacios, guiones, etc.
            telefono_limpio = ''.join(filter(str.isdigit, telefono))
            whatsapp_link = f"https://wa.me/57{telefono_limpio}?text={mensaje_codificado}"
    
    return render_template('pagos/ver_pago.html',
                         pago=pago,
                         whatsapp_link=whatsapp_link,
                         tiene_telefono=tiene_telefono)


# ============================================================
# RUTA PARA LISTAR TODOS LOS PAGOS (opcional)
# ============================================================
# routes/pagos.py

@ pagos_bp.route('/')
@login_required
def lista_pagos():
    """Lista todos los pagos del usuario con filtros"""
    from datetime import datetime, timedelta
    
    # Obtener parámetros de filtro
    filtro_fecha = request.args.get('fecha', '')  # hoy, semana, mes, personalizado
    fecha_desde = request.args.get('desde', '')
    fecha_hasta = request.args.get('hasta', '')
    metodo = request.args.get('metodo', '')
    busqueda = request.args.get('busqueda', '')
    
    # Base query
    query = PagoUnificado.query.filter_by(usuario_id=current_user.id)
    
    # Aplicar filtros de fecha
    hoy = date.today()
    
    if filtro_fecha == 'hoy':
        query = query.filter(PagoUnificado.fecha == hoy)
    elif filtro_fecha == 'semana':
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        query = query.filter(PagoUnificado.fecha >= inicio_semana)
    elif filtro_fecha == 'mes':
        inicio_mes = date(hoy.year, hoy.month, 1)
        query = query.filter(PagoUnificado.fecha >= inicio_mes)
    elif fecha_desde and fecha_hasta:
        query = query.filter(
            PagoUnificado.fecha >= datetime.strptime(fecha_desde, '%Y-%m-%d').date(),
            PagoUnificado.fecha <= datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
        )
    
    # Filtrar por método de pago
    if metodo:
        query = query.filter(PagoUnificado.metodo_pago == metodo)
    
    # Búsqueda por nombre de paciente o descripción
    if busqueda:
        query = query.filter(
            db.or_(
                PagoUnificado.paciente_nombre.ilike(f'%{busqueda}%'),
                PagoUnificado.descripcion.ilike(f'%{busqueda}%'),
                PagoUnificado.codigo.ilike(f'%{busqueda}%')
            )
        )
    
    # Ordenar por fecha descendente
    pagos = query.order_by(PagoUnificado.fecha.desc(), PagoUnificado.hora.desc()).all()
    
    # Calcular totales
    total_general = sum(p.monto for p in pagos)
    total_efectivo = sum(p.monto for p in pagos if p.metodo_pago == 'Efectivo')
    total_tarjeta = sum(p.monto for p in pagos if p.metodo_pago == 'Tarjeta')
    total_transferencia = sum(p.monto for p in pagos if p.metodo_pago == 'Transferencia')
    total_nequi = sum(p.monto for p in pagos if p.metodo_pago == 'Nequi')
    total_daviplata = sum(p.monto for p in pagos if p.metodo_pago == 'Daviplata')
    
    # Estadísticas
    total_pagos = len(pagos)
    pagos_rapidos = sum(1 for p in pagos if p.es_rapido)
    pagos_pacientes = total_pagos - pagos_rapidos
    
    return render_template(
        'pagos/lista.html',
        pagos=pagos,
        total_general=total_general,
        total_efectivo=total_efectivo,
        total_tarjeta=total_tarjeta,
        total_transferencia=total_transferencia,
        total_nequi=total_nequi,
        total_daviplata=total_daviplata,
        total_pagos=total_pagos,
        pagos_rapidos=pagos_rapidos,
        pagos_pacientes=pagos_pacientes,
        filtros={
            'fecha': filtro_fecha,
            'desde': fecha_desde,
            'hasta': fecha_hasta,
            'metodo': metodo,
            'busqueda': busqueda
        }
    )