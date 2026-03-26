# routes/pagos.py - PARTE SUPERIOR DEL ARCHIVO
from flask import Blueprint, render_template, request, flash, redirect, session, url_for, make_response
from flask_login import login_required, current_user
from datetime import date, datetime
from clinica.models import db, PagoUnificado
import random
import string
from io import BytesIO
from xhtml2pdf import pisa
import pytz

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
            fecha = datetime.strptime(request.form.get('fecha'), '%d/%m/%Y').date()
            colombia_tz = pytz.timezone('America/Bogota')
            hora = datetime.now(colombia_tz).time()
            descripcion = request.form.get('descripcion')
            monto = int(request.form.get('monto', 0))
            metodo_pago = request.form.get('metodo_pago')
            observacion = request.form.get('observacion')
            pagado_por = request.form.get('pagado_por')
            
            # NUEVO: Guardar teléfono si se proporcionó
            telefono = request.form.get('telefono', '').strip()
            
            # Obtener datos del paciente
            paciente_id = request.form.get('paciente_id', type=int)
            paciente_nombre = request.form.get('paciente_nombre')
            
            # Si viene paciente_id, verificar que existe
            if paciente_id:
                paciente = Paciente.query.get(paciente_id)
                if paciente:
                    paciente_nombre = f"{paciente.primer_nombre} {paciente.primer_apellido}"
                    es_rapido = False
                    # Usar el teléfono del paciente si no se proporcionó uno nuevo
                    if not telefono and paciente.telefono:
                        telefono = paciente.telefono
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
            
            # Guardar el teléfono en la sesión para usarlo en el recibo
            if telefono:
                session[f'telefono_pago_{nuevo_pago.id}'] = telefono
            
            return redirect(url_for('pagos.ver_pago', pago_id=nuevo_pago.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar el pago: {str(e)}', 'danger')
            return redirect(url_for('pagos.nuevo_pago'))
    
    # GET - Mostrar formulario
    today = date.today().strftime('%d/%m/%Y')
    return render_template('pagos/rapido.html', today=today)

# ============================================================
# RUTA PARA VER DETALLE DEL PAGO
# ============================================================

@pagos_bp.route('/<int:pago_id>')
@login_required
def ver_pago(pago_id):
    """Muestra el detalle de un pago y prepara enlace del PDF"""
    from clinica.models import PagoUnificado, Paciente
    import urllib.parse
    from flask import session
    
    pago = PagoUnificado.query.get_or_404(pago_id)
    
    # Verificar permisos
    if pago.usuario_id != current_user.id and not current_user.is_admin:
        flash('No tienes permiso para ver este pago', 'danger')
        return redirect(url_for('main.index'))
    
    # Variables para WhatsApp
    telefono = None
    whatsapp_link_pdf = None
    whatsapp_link_print = None
    tiene_telefono = False
    
    # 1. Si es un pago de paciente registrado, buscar su teléfono
    if pago.paciente_id:
        paciente = Paciente.query.get(pago.paciente_id)
        if paciente and paciente.telefono:
            telefono = paciente.telefono
            tiene_telefono = True
    
    # 2. Si es cobro rápido, buscar teléfono en la sesión
    else:
        telefono_session = session.get(f'telefono_pago_{pago.id}')
        if telefono_session:
            telefono = telefono_session
            tiene_telefono = True
    
    # Si tenemos teléfono, crear enlaces de WhatsApp
    if tiene_telefono and telefono:
        # Enlace para PDF con token
        pdf_url = url_for('pagos.generar_pdf', pago_id=pago.id, _external=True) + f"?token={pago.codigo}"
        
        # Enlace para captura con token
        print_url = url_for('pagos.print_recibo', pago_id=pago.id, _external=True) + f"?token={pago.codigo}"
        
        # Mensaje para PDF
        mensaje_pdf = f"""🧾 *RECIBO DE PAGO - CLÍNICA DENTAL*

*Código:* {pago.codigo}
*Paciente:* {pago.paciente_nombre}
*Fecha:* {pago.fecha.strftime('%d/%m/%Y')} {pago.hora.strftime('%H:%M')}
*Monto:* ${pago.monto:,.0f}
*Método:* {pago.metodo_pago}

📎 *Descarga tu recibo aquí:* {pdf_url}

¡Gracias por tu pago!"""
        
        # Mensaje para captura
        mensaje_print = f"""🧾 *RECIBO DE PAGO - CLÍNICA DENTAL*

*Código:* {pago.codigo}
*Paciente:* {pago.paciente_nombre}
*Fecha:* {pago.fecha.strftime('%d/%m/%Y')} {pago.hora.strftime('%H:%M')}
*Monto:* ${pago.monto:,.0f}
*Método:* {pago.metodo_pago}

📸 *Ver tu recibo aquí:* {print_url}

¡Gracias por tu pago!"""
        
        mensaje_pdf_codificado = urllib.parse.quote(mensaje_pdf)
        mensaje_print_codificado = urllib.parse.quote(mensaje_print)
        
        telefono_limpio = ''.join(filter(str.isdigit, telefono))
        whatsapp_link_pdf = f"https://wa.me/57{telefono_limpio}?text={mensaje_pdf_codificado}"
        whatsapp_link_print = f"https://wa.me/57{telefono_limpio}?text={mensaje_print_codificado}"
        
    return render_template('pagos/ver_pago.html',
                         pago=pago,
                         whatsapp_link_pdf=whatsapp_link_pdf,
                         whatsapp_link_print=whatsapp_link_print,
                         tiene_telefono=tiene_telefono)

# ============================================================
# RUTA PARA LISTAR TODOS LOS PAGOS
# ============================================================
from flask import request, render_template
from flask_login import login_required, current_user
from clinica.models import PagoUnificado
from clinica import db
from sqlalchemy import or_, and_, func
from datetime import datetime, timedelta

# ============================================================
# RUTA PARA LISTAR TODOS LOS PAGOS (CON PAGINACIÓN)
# ============================================================
# ============================================================
# RUTA PARA LISTAR TODOS LOS PAGOS (CON PAGINACIÓN)
# ============================================================
@pagos_bp.route('/')
@login_required
def lista_pagos():
    """Lista todos los pagos con filtros y paginación"""
    from sqlalchemy import or_, func
    from datetime import datetime, timedelta
    
    # Obtener parámetros de paginación
    page = request.args.get('page', 1, type=int)
    per_page = 7  # Número de pagos por página
    
    # DEBUG: Imprimir en consola
    print(f"=== DEBUG PAGINACIÓN ===")
    print(f"Página actual: {page}")
    print(f"Pagos por página: {per_page}")
    
    # Obtener filtros
    filtros = {
        'fecha': request.args.get('fecha', ''),
        'desde': request.args.get('desde', ''),
        'hasta': request.args.get('hasta', ''),
        'metodo': request.args.get('metodo', ''),
        'busqueda': request.args.get('busqueda', '')
    }
    
    # Query base
    query = PagoUnificado.query.filter_by(usuario_id=current_user.id)
    
    # Aplicar filtros
    if filtros['fecha'] == 'hoy':
        query = query.filter(func.date(PagoUnificado.fecha) == datetime.now().date())
    elif filtros['fecha'] == 'semana':
        inicio_semana = datetime.now().date() - timedelta(days=datetime.now().weekday())
        query = query.filter(PagoUnificado.fecha >= inicio_semana)
    elif filtros['fecha'] == 'mes':
        query = query.filter(
            PagoUnificado.fecha >= datetime.now().replace(day=1).date()
        )
    elif filtros['fecha'] == 'personalizado' and filtros['desde'] and filtros['hasta']:
        try:
            desde = datetime.strptime(filtros['desde'], '%Y-%m-%d').date()
            hasta = datetime.strptime(filtros['hasta'], '%Y-%m-%d').date()
            query = query.filter(
                PagoUnificado.fecha >= desde,
                PagoUnificado.fecha <= hasta
            )
        except ValueError:
            pass
    
    if filtros['metodo']:
        query = query.filter(PagoUnificado.metodo_pago == filtros['metodo'])
    
    if filtros['busqueda']:
        busqueda = f"%{filtros['busqueda']}%"
        query = query.filter(
            or_(
                PagoUnificado.codigo.ilike(busqueda),
                PagoUnificado.paciente_nombre.ilike(busqueda),
                PagoUnificado.descripcion.ilike(busqueda)
            )
        )
    
    # Ordenar por fecha descendente
    query = query.order_by(PagoUnificado.fecha.desc(), PagoUnificado.hora.desc())
    
    # Paginación
    paginacion = query.paginate(page=page, per_page=per_page, error_out=False)
    pagos = paginacion.items
    
    # DEBUG: Imprimir información
    print(f"Total de pagos: {paginacion.total}")
    print(f"Total de páginas: {paginacion.pages}")
    print(f"Pagos en esta página: {len(pagos)}")
    print(f"=======================")
    
    # Estadísticas generales (sin paginación)
    total_general_all = db.session.query(func.sum(PagoUnificado.monto)).filter_by(usuario_id=current_user.id).scalar() or 0
    total_efectivo = db.session.query(func.sum(PagoUnificado.monto)).filter_by(usuario_id=current_user.id, metodo_pago='Efectivo').scalar() or 0
    total_bancolombia = db.session.query(func.sum(PagoUnificado.monto)).filter_by(usuario_id=current_user.id, metodo_pago='Bancolombia').scalar() or 0
    total_nequi = db.session.query(func.sum(PagoUnificado.monto)).filter_by(usuario_id=current_user.id, metodo_pago='Nequi').scalar() or 0
    total_tarjeta = db.session.query(func.sum(PagoUnificado.monto)).filter_by(usuario_id=current_user.id, metodo_pago='Tarjeta').scalar() or 0
    total_otro = db.session.query(func.sum(PagoUnificado.monto)).filter_by(usuario_id=current_user.id, metodo_pago='Otro').scalar() or 0
    total_pagos = PagoUnificado.query.filter_by(usuario_id=current_user.id).count()
    pagos_pacientes = PagoUnificado.query.filter_by(usuario_id=current_user.id, es_rapido=False).count()
    pagos_rapidos = PagoUnificado.query.filter_by(usuario_id=current_user.id, es_rapido=True).count()
    
    return render_template(
        'pagos/lista.html',
        pagos=pagos,
        paginacion=paginacion,
        total_general=total_general_all,
        total_efectivo=total_efectivo,
        total_bancolombia=total_bancolombia,
        total_nequi=total_nequi,
        total_tarjeta=total_tarjeta,
        total_otro=total_otro,
        total_pagos=total_pagos,
        pagos_pacientes=pagos_pacientes,
        pagos_rapidos=pagos_rapidos,
        filtros=filtros
    )

# ============================================================
# RUTA PARA GENERAR PDF CON XHTML2PDF (PÚBLICA CON TOKEN)
# ============================================================
@pagos_bp.route('/<int:pago_id>/pdf')
def generar_pdf(pago_id):
    from clinica.models import PagoUnificado, Usuario
    from datetime import datetime
    
    pago = PagoUnificado.query.get_or_404(pago_id)
    
    # Verificar por token en lugar de login
    token = request.args.get('token')
    if token != pago.codigo:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('main.index'))
    
    # Obtener el usuario que creó el pago
    usuario = Usuario.query.get(pago.usuario_id)
    nombre_usuario = usuario.nombre_completo or usuario.username if usuario else 'Sistema'
    
    html = render_template('pagos/recibo_pdf_xhtml.html', 
                         pago=pago,
                         now=datetime.now,
                         nombre_usuario=nombre_usuario)
    
    try:
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(
            BytesIO(html.encode('utf-8')), 
            dest=pdf_buffer,
            encoding='utf-8'
        )
        
        if pisa_status.err:
            return "Error al generar PDF", 500
        
        pdf = pdf_buffer.getvalue()
        
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=recibo_{pago.codigo}.pdf'
        
        return response
        
    except Exception as e:
        return f"Error: {str(e)}", 500
    
# ============================================================
# RUTA PARA VISTA LIMPIA DE CAPTURA (PÚBLICA CON TOKEN)
# ============================================================
@pagos_bp.route('/<int:pago_id>/print')
def print_recibo(pago_id):
    """Vista limpia del recibo para captura de pantalla"""
    from clinica.models import PagoUnificado
    from datetime import datetime
    
    pago = PagoUnificado.query.get_or_404(pago_id)
    
    # DEBUG: Imprimir valores para diagnóstico
    token = request.args.get('token')
    print(f"=== DEBUG PRINT ===")
    print(f"Pago ID: {pago_id}")
    print(f"Código pago: '{pago.codigo}'")
    print(f"Token recibido: '{token}'")
    print(f"Token == Código: {token == pago.codigo}")
    print(f"Token length: {len(token) if token else 0}")
    print(f"Código length: {len(pago.codigo)}")
    print(f"==================")
    
    if token != pago.codigo:
        return f"Acceso no autorizado. Token recibido: '{token}', Esperado: '{pago.codigo}'", 401
    
    return render_template('pagos/recibo_print.html',
                         pago=pago,
                         now=datetime.now,
                         current_user=None,
                         whatsapp_link=None)