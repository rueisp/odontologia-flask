from flask import render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from datetime import date, datetime, time, timedelta
import calendar
from sqlalchemy import extract, or_
from urllib.parse import quote_plus
import pytz
from ...models import db, Cita, Paciente
from clinica.campos_activos import CAMPOS_PACIENTE_ACTIVOS
from . import calendario_bp

NOMBRES_MESES_ESP = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

def construir_dias_del_mes(anio, mes, citas_del_mes_obj, dia_hoy_local, mes_hoy_local, anio_hoy_local):
    dias_calendario = []
    primer_dia_obj = date(anio, mes, 1)
    total_dias_en_mes = calendar.monthrange(anio, mes)[1]
    dia_semana_inicio = (primer_dia_obj.weekday() + 1) % 7

    for _ in range(dia_semana_inicio):
        dias_calendario.append({'fecha': None, 'hoy': False, 'citas': []})

    for dia_num in range(1, total_dias_en_mes + 1):
        fecha_actual_dia = date(anio, mes, dia_num)
        citas_en_dia_actual = [c for c in citas_del_mes_obj if date.fromisoformat(c['fecha']) == fecha_actual_dia]
        citas_preparadas = []
        for cita_dict in citas_en_dia_actual:
            citas_preparadas.append({
                'id': cita_dict['id'],
                'fecha': cita_dict['fecha'],
                'hora': cita_dict['hora'],
                'motivo': cita_dict['motivo'],
                'doctor': cita_dict['doctor'],
                'observaciones': cita_dict['observaciones'],
                'estado': cita_dict['estado'],
                'paciente_id': cita_dict['paciente_id'],
                'paciente_nombre_completo': cita_dict['paciente_nombre_completo'],
                'paciente_telefono_str': cita_dict['paciente_telefono_str'],
                'edit_url': cita_dict['edit_url'],
                'delete_url': cita_dict['delete_url'],
                'next_url_encoded': cita_dict['next_url_encoded']
            })
        es_hoy = (fecha_actual_dia.day == dia_hoy_local and
                  fecha_actual_dia.month == mes_hoy_local and
                  fecha_actual_dia.year == anio_hoy_local)
        dias_calendario.append({
            'fecha': fecha_actual_dia,
            'hoy': es_hoy,
            'citas': citas_preparadas
        })

    total_celdas_actual = len(dias_calendario)
    celdas_vacias_final = (7 - total_celdas_actual % 7) % 7
    for _ in range(celdas_vacias_final):
        dias_calendario.append({'fecha': None, 'hoy': False, 'citas': []})
    return dias_calendario

@calendario_bp.route('/')
@login_required
def mostrar_calendario():
    local_timezone = pytz.timezone('America/Bogota')
    now_in_local_tz = datetime.now(local_timezone)
    anio_actual = request.args.get('anio', default=now_in_local_tz.year, type=int)
    mes_actual = request.args.get('mes', default=now_in_local_tz.month, type=int)
    dia_hoy_local = now_in_local_tz.day
    mes_hoy_local = now_in_local_tz.month
    anio_hoy_local = now_in_local_tz.year

    try:
        date(anio_actual, mes_actual, 1)
    except ValueError:
        flash("Mes o año inválido.", "warning")
        anio_actual = now_in_local_tz.year
        mes_actual = now_in_local_tz.month

    query_citas = Cita.query.options(
        db.load_only(
            Cita.id, Cita.paciente_id, Cita.fecha, Cita.hora, Cita.motivo,
            Cita.doctor, Cita.estado, Cita.observaciones,
            Cita.paciente_nombres_str, Cita.paciente_apellidos_str, Cita.paciente_telefono_str
        )
    ).filter(
        Cita.is_deleted == False,
        extract('year', Cita.fecha) == anio_actual,
        extract('month', Cita.fecha) == mes_actual
    )
    
    if not current_user.is_admin:
        from ...models import Paciente
        paciente_ids_subq = db.session.query(Paciente.id).filter(
            Paciente.odontologo_id == current_user.id,
            Paciente.is_deleted == False
        ).subquery()
        query_citas = query_citas.filter(
            or_(
                Cita.paciente_id.in_(paciente_ids_subq),
                Cita.paciente_id == None
            )
        )
    else:
        from ...models import Paciente
        query_citas = query_citas.outerjoin(
            Paciente, Cita.paciente_id == Paciente.id
        ).filter(
            or_(
                Paciente.is_deleted == False,
                Cita.paciente_id == None
            )
        )

    citas_del_mes = query_citas.order_by(Cita.fecha, Cita.hora).all()
    current_full_path_for_template = request.full_path

    citas_para_construir = []
    for cita_obj in citas_del_mes:
        paciente_nombre_completo = "Paciente sin registrar"
        if cita_obj.paciente_id:
            from ...models import Paciente
            paciente = Paciente.query.get(cita_obj.paciente_id)
            if paciente and not paciente.is_deleted:
                paciente_nombre_completo = f"{paciente.nombres} {paciente.apellidos}"
            else:
                if cita_obj.paciente_nombres_str and cita_obj.paciente_apellidos_str:
                    paciente_nombre_completo = f"{cita_obj.paciente_nombres_str} {cita_obj.paciente_apellidos_str}"
                elif cita_obj.paciente_nombres_str:
                    paciente_nombre_completo = cita_obj.paciente_nombres_str
        else:
            if cita_obj.paciente_nombres_str and cita_obj.paciente_apellidos_str:
                paciente_nombre_completo = f"{cita_obj.paciente_nombres_str} {cita_obj.paciente_apellidos_str}"
            elif cita_obj.paciente_nombres_str:
                paciente_nombre_completo = cita_obj.paciente_nombres_str
        
        citas_para_construir.append({
            'id': cita_obj.id,
            'fecha': cita_obj.fecha.strftime('%Y-%m-%d'),
            'hora': cita_obj.hora.strftime('%H:%M'),
            'motivo': cita_obj.motivo,
            'doctor': cita_obj.doctor,
            'observaciones': cita_obj.observaciones,
            'estado': cita_obj.estado,
            'paciente_id': cita_obj.paciente_id,
            'paciente_nombre_completo': paciente_nombre_completo,
            'paciente_telefono_str': cita_obj.paciente_telefono_str,
            'edit_url': url_for('calendario.editar_cita', cita_id=cita_obj.id, next=current_full_path_for_template),
            'delete_url': url_for('calendario.eliminar_cita', cita_id=cita_obj.id, next=current_full_path_for_template),
            'next_url_encoded': quote_plus(current_full_path_for_template)
        })

    dias_render = construir_dias_del_mes(anio_actual, mes_actual, citas_para_construir,
                                         dia_hoy_local, mes_hoy_local, anio_hoy_local)
    nombre_mes_actual_display = NOMBRES_MESES_ESP[mes_actual-1]

    return render_template('calendario.html',
                           anio=anio_actual,
                           mes=mes_actual,
                           nombres_meses=NOMBRES_MESES_ESP,
                           nombre_mes_display=nombre_mes_actual_display,
                           dias=dias_render,
                           anio_hoy=anio_hoy_local,
                           mes_hoy=mes_hoy_local,
                           dia_hoy=dia_hoy_local,
                           current_full_path=current_full_path_for_template)


@calendario_bp.route('/dia', methods=['GET'])
@login_required
def vista_diaria():
    fecha_str = request.args.get('fecha')
    if fecha_str:
        try:
            fecha_seleccionada = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            fecha_seleccionada = date.today()
    else:
        fecha_seleccionada = date.today()
    
    query_citas = Cita.query.options(
        db.load_only(
            Cita.id, Cita.paciente_id, Cita.fecha, Cita.hora, Cita.motivo,
            Cita.doctor, Cita.estado,
            Cita.paciente_nombres_str, Cita.paciente_apellidos_str, Cita.paciente_telefono_str
        )
    ).filter(
        Cita.fecha == fecha_seleccionada,
        Cita.is_deleted == False
    )
    
    citas_del_dia = query_citas.all()
    paciente_ids = list(set([c.paciente_id for c in citas_del_dia if c.paciente_id]))
    
    pacientes_dict = {}
    if paciente_ids:
        pacientes = Paciente.query.options(
            db.load_only(Paciente.id, Paciente.nombres, Paciente.apellidos, Paciente.telefono, Paciente.odontologo_id)
        ).filter(Paciente.id.in_(paciente_ids)).all()
        for p in pacientes:
            pacientes_dict[p.id] = p
    
    citas_por_hora = {}
    for cita in citas_del_dia:
        hora_key = cita.hora.strftime('%H:%M')
        
        if cita.paciente_id and cita.paciente_id in pacientes_dict:
            paciente = pacientes_dict[cita.paciente_id]
            paciente_nombre = paciente.nombres or ''
            paciente_apellidos = paciente.apellidos or ''
            paciente_telefono = paciente.telefono or ''
        else:
            paciente_nombre = cita.paciente_nombres_str or ''
            paciente_apellidos = cita.paciente_apellidos_str or ''
            paciente_telefono = cita.paciente_telefono_str or ''
        
        if not current_user.is_admin:
            if cita.paciente_id and cita.paciente_id in pacientes_dict:
                if pacientes_dict[cita.paciente_id].odontologo_id != current_user.id:
                    continue
        
        citas_por_hora[hora_key] = {
            'id': cita.id,
            'paciente_nombre': paciente_nombre,
            'paciente_apellidos': paciente_apellidos,
            'paciente_telefono': paciente_telefono,
            'motivo': cita.motivo or '',
            'doctor': cita.doctor,
            'estado': cita.estado,
            'edit_url': url_for('calendario.editar_cita', cita_id=cita.id, next=request.full_path)
        }
    
    franjas = []
    hora_inicio = time(8, 0)
    hora_fin = time(18, 0)
    hora_actual = datetime.combine(fecha_seleccionada, hora_inicio)
    hora_fin_dt = datetime.combine(fecha_seleccionada, hora_fin)
    
    while hora_actual <= hora_fin_dt:
        hora_str = hora_actual.strftime('%H:%M')
        franjas.append({
            'hora': hora_str,
            'hora_display': hora_actual.strftime('%I:%M %p'),
            'cita': citas_por_hora.get(hora_str, None)
        })
        hora_actual += timedelta(minutes=30)
    
    mes_actual = fecha_seleccionada.month
    anio_actual = fecha_seleccionada.year
    nombre_mes = NOMBRES_MESES_ESP[mes_actual - 1]
    
    cal = calendar.monthcalendar(anio_actual, mes_actual)
    dias_del_mes = []
    for semana in cal:
        fila = []
        for dia in semana:
            if dia != 0:
                try:
                    fecha_dia = date(anio_actual, mes_actual, dia)
                    fila.append({
                        'dia': dia,
                        'fecha': fecha_dia,
                        'es_seleccionada': fecha_dia == fecha_seleccionada
                    })
                except ValueError:
                    fila.append(None)
            else:
                fila.append(None)
        dias_del_mes.append(fila)
    
    return render_template('vista_diaria.html',
                          fecha_seleccionada=fecha_seleccionada,
                          franjas=franjas,
                          mes_actual=mes_actual,
                          anio_actual=anio_actual,
                          nombre_mes=nombre_mes,
                          dias_del_mes=dias_del_mes,
                          nombres_meses=NOMBRES_MESES_ESP,
                          timedelta=timedelta,
                          date=date)