"""
Rutas HTTP para el módulo de pacientes.

Este módulo contiene solo las rutas HTTP, delegando la lógica de negocio
a pacientes_services.py para mejor mantenibilidad.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import date, datetime
from clinica.models import Paciente, PagoPaciente
from ..extensions import db
import json 
from sqlalchemy import or_
import cloudinary.uploader  # <--- AGREGA ESTO
from clinica.decorators.limites import verificar_limite_pacientes
from sqlalchemy.orm import load_only
from clinica.campos_activos import load_only_paciente_activo
import pytz
# Importar servicios
# Importar servicios de pacientes
from .pacientes.pacientes_services import (
    listar_pacientes_service,
    obtener_paciente_service,
    crear_paciente_service,
    editar_paciente_service,
    borrar_paciente_service
)
from clinica.decorators.limites import (
    verificar_limite_pacientes,
    verificar_suscripcion_activa
)

# Importar servicios de evoluciones
from .pacientes.pacientes_evoluciones import agregar_evolucion_service
from clinica.decorators.limites import solo_lectura_si_expirado

pacientes_bp = Blueprint('pacientes', __name__, url_prefix='/pacientes')


@pacientes_bp.route('/crear', methods=['GET', 'POST'])
@login_required
@verificar_suscripcion_activa
@verificar_limite_pacientes
def crear_paciente():
    """Crea un nuevo paciente"""
    if request.method == 'POST':
        resultado = crear_paciente_service(request.form, request.files, current_user)
        
        if resultado['success']:
            flash(resultado['message'], 'success')
            return redirect(url_for('pacientes.lista_pacientes'))
        else:
            flash(resultado['message'], 'danger')
            return render_template('registrar_paciente.html', paciente=None)
    
    # GET - Mostrar formulario vacío
    return render_template('registrar_paciente.html', paciente=None)


@pacientes_bp.route('/lista', methods=['GET'])
@login_required
@verificar_suscripcion_activa
def lista_pacientes():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('buscar', '').strip()
    
    # ✅ CONSULTA OPTIMIZADA - Solo campos activos
    query = db.session.query(Paciente).options(
        load_only_paciente_activo()
    ).filter(Paciente.is_deleted == False)

    # Filtrar por odontólogo si no es admin
    if not current_user.is_admin:
        query = query.filter(Paciente.odontologo_id == current_user.id)

    # Lógica de búsqueda
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            or_(
                Paciente.nombres.ilike(search_term),
                Paciente.apellidos.ilike(search_term),
                Paciente.documento.ilike(search_term)
            )
        )

    # Ordenar y paginar
    pacientes = query.order_by(Paciente.id.desc()).paginate(page=page, per_page=6, error_out=False)

    return render_template('pacientes.html', pacientes=pacientes, buscar=search_query)

@pacientes_bp.route('/<int:id>', methods=['GET', 'POST'])
@login_required
@verificar_suscripcion_activa
def mostrar_paciente(id):
    """Muestra un paciente y permite agregar evoluciones"""
    if request.method == 'POST':
        descripcion = request.form.get('descripcion')
        resultado = agregar_evolucion_service(id, descripcion, current_user)
        flash(resultado['message'], 'success' if resultado['success'] else 'warning')
        return redirect(url_for('pacientes.mostrar_paciente', id=id))

    paciente_data, evoluciones_procesadas, full_public_id_trazos = obtener_paciente_service(id, current_user)
    
    # 🔥 CONVERTIR FECHA DE STRING A OBJETO DATE 🔥
    from datetime import datetime
    if 'fecha_nacimiento' in paciente_data and isinstance(paciente_data['fecha_nacimiento'], str):
        try:
            paciente_data['fecha_nacimiento'] = datetime.strptime(paciente_data['fecha_nacimiento'], '%d/%m/%Y').date()
        except:
            pass
    
    return render_template('mostrar_paciente.html',
                          paciente=paciente_data,
                          evoluciones_ordenadas=evoluciones_procesadas,
                          full_public_id_trazos=full_public_id_trazos,
                          current_full_path=request.full_path)


@pacientes_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@verificar_suscripcion_activa
@solo_lectura_si_expirado
def editar_paciente(id):
    """Edita un paciente existente - Versión simplificada"""
    
    if request.method == 'POST':
        # Procesar el formulario de edición
        resultado = editar_paciente_service(id, request.form, request.files, current_user)
        
        if resultado['success']:
            flash(resultado['message'], 'success')
            # Redirigir a la vista del paciente
            return redirect(url_for('pacientes.mostrar_paciente', id=id))
        else:
            flash(resultado['message'], 'danger')
            return redirect(url_for('pacientes.editar_paciente', id=id))

    # --- LÓGICA GET - USANDO EL SERVICIO OPTIMIZADO ---
    # Obtener datos del paciente con SOLO los campos necesarios
    paciente_data, evoluciones, public_id = obtener_paciente_service(id, current_user)
    
    # Convertir el diccionario a un objeto para el template
    from types import SimpleNamespace
    paciente = SimpleNamespace(**paciente_data)
    
    # Formatear fecha para el input type="date"
    if hasattr(paciente, 'fecha_nacimiento') and paciente.fecha_nacimiento and paciente.fecha_nacimiento != 'N/A':
        try:
            from datetime import datetime
            fecha_obj = datetime.strptime(paciente.fecha_nacimiento, '%d/%m/%Y')
            paciente.fecha_nacimiento = fecha_obj.strftime('%Y-%m-%d')
            # Guardar versión para mostrar en formato dd/mm/yyyy
            paciente.fecha_nacimiento_display = fecha_obj.strftime('%d/%m/%Y')
        except:
            paciente.fecha_nacimiento = ''
            paciente.fecha_nacimiento_display = ''
    else:
        paciente.fecha_nacimiento_display = ''

    # Renderizar template sin datos de ubicación
    return render_template('editar_paciente.html', 
                           paciente=paciente)

@pacientes_bp.route('/<int:id>/borrar', methods=['POST'])
@login_required
@verificar_suscripcion_activa
@solo_lectura_si_expirado
def borrar_paciente(id):
    """Borra un paciente (soft delete)"""
    resultado = borrar_paciente_service(id, current_user)
    flash(resultado['message'], 'success' if resultado['success'] else 'danger')
    return redirect(url_for('pacientes.lista_pacientes'))

# ============================================================
# RUTAS PARA CONTROL DE PAGOS DE PACIENTES
# ============================================================

@pacientes_bp.route('/<int:paciente_id>/pagos', methods=['GET'])
@login_required
def pagos_paciente(paciente_id):
    """Muestra el historial de pagos de un paciente (sistema unificado)"""
    from clinica.models import PagoUnificado, Paciente
    from datetime import date
    
    paciente = Paciente.query.filter_by(id=paciente_id, is_deleted=False).first_or_404()
    
    # Verificar permisos
    if not current_user.is_admin and paciente.odontologo_id != current_user.id:
        flash('No tienes permiso para ver este paciente.', 'danger')
        return redirect(url_for('pacientes.lista_pacientes'))
    
    # Obtener pagos del nuevo sistema (ordenados por fecha descendente)
    pagos = PagoUnificado.query.filter_by(paciente_id=paciente_id).order_by(PagoUnificado.fecha.desc(), PagoUnificado.hora.desc()).all()
    
    # Calcular total
    total_pagos = sum(p.monto for p in pagos)
    today = date.today().isoformat()
    
    return render_template('pacientes/pagos_paciente.html',
                         paciente=paciente,
                         pagos=pagos,
                         total_pagos=total_pagos,
                         today=today)


# En routes/pacientes.py - NUEVA RUTA (reemplaza a agregar_pago_paciente)
@pacientes_bp.route('/<int:paciente_id>/pagos/nuevo', methods=['POST'])
@login_required
def agregar_pago_paciente_unificado_nuevo(paciente_id):
    """Agrega un nuevo pago usando el sistema unificado"""
    from clinica.models import PagoUnificado, Paciente
    import random
    import string
    from datetime import datetime
    
    paciente = Paciente.query.filter_by(id=paciente_id, is_deleted=False).first_or_404()
    
    # Verificar permisos
    if not current_user.is_admin and paciente.odontologo_id != current_user.id:
        flash('No tienes permiso para modificar este paciente.', 'danger')
        return redirect(url_for('pacientes.lista_pacientes'))
    
    try:
        # Generar código único
        fecha_str = date.today().strftime('%Y%m%d')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        codigo = f"P-{fecha_str}-{random_str}"
        
        # Definir zona horaria de Colombia
        colombia_tz = pytz.timezone('America/Bogota')
        
        nuevo_pago = PagoUnificado(
            paciente_id=paciente_id,
            paciente_nombre=f"{paciente.primer_nombre} {paciente.primer_apellido}",
            fecha=datetime.strptime(request.form.get('fecha'), '%d/%m/%Y').date(),
            hora=datetime.now(colombia_tz).time(),
            descripcion=request.form.get('descripcion'),
            monto=int(request.form.get('monto', 0)),
            metodo_pago=request.form.get('metodo_pago') or 'Efectivo',
            observacion=request.form.get('observacion'),
            pagado_por=request.form.get('pagado_por'),
            codigo=codigo,
            es_rapido=False,
            usuario_id=current_user.id
        )
        
        db.session.add(nuevo_pago)
        db.session.commit()
        
        flash('Pago registrado correctamente en el nuevo sistema.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al registrar el pago: {str(e)}', 'danger')
    
    return redirect(url_for('pacientes.pagos_paciente', paciente_id=paciente_id))

# ============================================================
# RUTAS PARA EDITAR Y ELIMINAR PAGOS DE PACIENTES
# ============================================================

@pacientes_bp.route('/pago/<int:pago_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_pago_paciente(pago_id):
    """Edita un pago existente (sistema unificado)"""
    from clinica.models import PagoUnificado, Paciente
    from datetime import date
    
    pago = PagoUnificado.query.get_or_404(pago_id)
    
    # Obtener paciente si existe
    paciente = None
    if pago.paciente_id:
        paciente = Paciente.query.get(pago.paciente_id)
    
    # Verificar permisos
    if pago.usuario_id != current_user.id and not current_user.is_admin:
        flash('No tienes permiso para modificar este pago.', 'danger')
        return redirect(url_for('pacientes.lista_pacientes'))
    
    if request.method == 'POST':
        try:
            pago.fecha = datetime.strptime(request.form.get('fecha'), '%d/%m/%Y').date()
            pago.descripcion = request.form.get('descripcion')
            pago.monto = int(request.form.get('monto', 0))
            pago.metodo_pago = request.form.get('metodo_pago')
            pago.observacion = request.form.get('observacion')
            pago.pagado_por = request.form.get('pagado_por')
            
            db.session.commit()
            flash('Pago actualizado correctamente.', 'success')
            
            # Redirigir según el tipo de pago
            if pago.paciente_id:
                return redirect(url_for('pacientes.pagos_paciente', paciente_id=pago.paciente_id))
            else:
                return redirect(url_for('pagos.lista_pagos'))
                
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el pago: {str(e)}', 'danger')
            return redirect(request.url)
    
    # GET: mostrar formulario
    today = date.today().isoformat()
    return render_template('pacientes/editar_pago_paciente.html',
                         pago=pago,
                         paciente=paciente,
                         today=today)


@pacientes_bp.route('/pago/<int:pago_id>/borrar', methods=['POST'])
@login_required
def borrar_pago_paciente(pago_id):
    """Elimina un pago del sistema unificado"""
    from clinica.models import PagoUnificado, Paciente
    
    pago = PagoUnificado.query.get_or_404(pago_id)
    
    # Guardar datos para redirección
    paciente_id = pago.paciente_id
    es_rapido = pago.es_rapido
    
    # Verificar permisos
    if pago.usuario_id != current_user.id and not current_user.is_admin:
        flash('No tienes permiso para eliminar este pago.', 'danger')
        return redirect(url_for('pacientes.lista_pacientes'))
    
    try:
        db.session.delete(pago)
        db.session.commit()
        flash('Pago eliminado correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el pago: {str(e)}', 'danger')
    
    # Redirigir según el tipo de pago
    if paciente_id and not es_rapido:
        return redirect(url_for('pacientes.pagos_paciente', paciente_id=paciente_id))
    else:
        return redirect(url_for('pagos.lista_pagos'))
    
    
    
@pacientes_bp.route('/obtener_paciente_ajax/<int:id>', methods=['GET'])
@login_required
def obtener_paciente_ajax(id):
    """Endpoint JSON para el panel derecho del dashboard"""
    try:
        from .pacientes.pacientes_services import obtener_paciente_service
        from clinica.models import Cita
        from datetime import date, datetime
        from sqlalchemy import or_
        
        paciente_data, evoluciones, public_id = obtener_paciente_service(id, current_user)
        
        # --- OBTENER DATOS DE CITAS REALES ---
        # Última cita (fecha anterior a hoy)
        ultima_cita = Cita.query.filter(
            Cita.paciente_id == id,
            Cita.is_deleted == False,
            Cita.fecha < date.today()
        ).order_by(
            Cita.fecha.desc(), 
            Cita.hora.desc()
        ).first()
        
        # Próxima cita (fecha posterior a hoy, o hoy pero con hora posterior)
        proxima_cita = Cita.query.filter(
            Cita.paciente_id == id,
            Cita.is_deleted == False,
            or_(
                Cita.fecha > date.today(),
                (Cita.fecha == date.today()) & (Cita.hora > datetime.now().time())
            )
        ).order_by(Cita.fecha, Cita.hora).first()
        
        # Formatear última cita
        ultima_cita_info = "No hay citas anteriores"
        if ultima_cita:
            fecha_str = ultima_cita.fecha.strftime('%d/%m/%Y')
            hora_str = ultima_cita.hora.strftime('%H:%M') if ultima_cita.hora else ''
            motivo = ultima_cita.motivo or 'Sin motivo'
            ultima_cita_info = f"{fecha_str} {hora_str} - {motivo}"
        
        # Formatear próxima cita
        proxima_cita_info = "No tiene próximas citas"
        if proxima_cita:
            fecha_str = proxima_cita.fecha.strftime('%d/%m/%Y')
            hora_str = proxima_cita.hora.strftime('%H:%M') if proxima_cita.hora else ''
            motivo = proxima_cita.motivo or 'Sin motivo'
            proxima_cita_info = f"{fecha_str} {hora_str} - {motivo}"
        
        # Mapear los campos
        response_data = {
            'id': paciente_data.get('id'),
            'nombre': f"{paciente_data.get('primer_nombre', '')} {paciente_data.get('primer_apellido', '')}".strip(),
            'documento': paciente_data.get('documento', 'No especificado'),
            'telefono': paciente_data.get('telefono', 'No especificado'),
            'edad': paciente_data.get('edad', 'No especificada'),
            'fecha_nacimiento': paciente_data.get('fecha_nacimiento', 'No especificado'),
            'direccion': paciente_data.get('direccion', 'No especificado'),
            'barrio': paciente_data.get('barrio', 'No especificado'),
            'email': paciente_data.get('email', 'No especificado'),
            'alergias': paciente_data.get('alergias', 'No especificado'),
            'motivo_consulta': paciente_data.get('motivo_consulta', 'No especificado'),
            'enfermedad_actual': paciente_data.get('enfermedad_actual', 'No especificado'),
            'observaciones': paciente_data.get('observaciones', 'No especificado'),
            'dentigrama_url': paciente_data.get('dentigrama_canvas', None),
            'ultima_cita_info': ultima_cita_info,
            'proxima_cita_paciente_info': proxima_cita_info
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error en obtener_paciente_ajax: {e}")
        return jsonify({'error': str(e)}), 500
    

