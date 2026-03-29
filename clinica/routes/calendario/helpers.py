from datetime import date
import calendar


def construir_dias_del_mes(anio, mes, citas_del_mes_obj, dia_hoy_local, mes_hoy_local, anio_hoy_local):
    """Construye la estructura de días del mes para el calendario"""
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


def is_safe_url(target):
    """Verifica si una URL es segura para redirigir"""
    from urllib.parse import urlparse, urljoin
    from flask import request
    
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


NOMBRES_MESES_ESP = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]