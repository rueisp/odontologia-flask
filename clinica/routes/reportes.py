# clinica/routes/reportes.py

from flask import Blueprint, render_template, request, flash, send_file, current_app
from flask_login import login_required
from datetime import datetime, time, timedelta
import io
import zipfile
import pytz

# --- IMPORTACIONES CLAVE ---
from ..extensions import db
from ..models import Factura, Cita, Paciente, Procedimiento

# Creamos el Blueprint
reportes_bp = Blueprint('reportes', __name__)


@reportes_bp.route('/reportes', methods=['GET', 'POST'])
@login_required
def vista_reportes():
    if request.method == 'POST':
        fecha_inicio_str = request.form.get('fecha_inicio')
        fecha_fin_str = request.form.get('fecha_fin')

        if not fecha_inicio_str or not fecha_fin_str:
            flash("Por favor, selecciona un rango de fechas válido.", "danger")
            return render_template('reportes.html')

        try:
            # Define la zona horaria local
            local_timezone = pytz.timezone('America/Bogota')

            # 1. Convertir las cadenas de fecha a objetos date locales
            fecha_inicio_local_date = datetime.strptime(fecha_inicio_str, '%m/%d/%Y').date()
            fecha_fin_local_date = datetime.strptime(fecha_fin_str, '%m/%d/%Y').date()

            # Calcular los límites UTC exactos para la consulta
            rango_inicio_utc = local_timezone.localize(datetime.combine(fecha_inicio_local_date, time.min)).astimezone(pytz.utc)
            rango_fin_siguiente_dia_local = fecha_fin_local_date + timedelta(days=1)
            rango_fin_utc = local_timezone.localize(datetime.combine(rango_fin_siguiente_dia_local, time.min)).astimezone(pytz.utc)

            # Consultar facturas
            facturas_en_periodo = Factura.query.filter(
                Factura.fecha_factura >= rango_inicio_utc,
                Factura.fecha_factura < rango_fin_utc
            ).order_by(Factura.fecha_factura.desc()).all()

            if not facturas_en_periodo:
                flash('No se encontraron facturas generadas en el período seleccionado.', 'warning')
                return render_template('reportes.html')

            # --- PREPARAR CONTENEDORES PARA RIPS ---
            lineas_af = []
            lineas_us = []
            lineas_ac = []
            lineas_ap = []
            
            pacientes_procesados = set()

            # Para los nombres de archivo RIPS
            fecha_para_nombre_rips = datetime.combine(fecha_inicio_local_date, time.min)

            # --- PROCESAR CADA FACTURA ---
            for factura in facturas_en_periodo:
                paciente = factura.paciente
                if not paciente: 
                    current_app.logger.warning(f"Factura {factura.id} sin paciente asociado, se omite.")
                    continue

                edad = (datetime.now().date() - paciente.fecha_nacimiento).days // 365 if paciente.fecha_nacimiento else 0

                # --- LÓGICA US (USUARIOS) ---
                if paciente.id not in pacientes_procesados:
                    # Usamos los campos separados de la base de datos
                    primer_apellido = paciente.primer_apellido or ''
                    segundo_apellido = paciente.segundo_apellido or ''
                    primer_nombre = paciente.primer_nombre or ''
                    segundo_nombre = paciente.segundo_nombre or ''

                    linea_us = [
                        paciente.tipo_documento or '',
                        paciente.documento or '',
                        paciente.aseguradora if paciente.aseguradora and paciente.aseguradora.strip() else "EPS001",
                        "1", # Tipo de usuario (1=Contributivo, hardcoded default por ahora)
                        primer_apellido,
                        segundo_apellido,
                        primer_nombre,
                        segundo_nombre,
                        str(edad),
                        "1" if paciente.genero == 'Masculino' else "2",
                        "05",    # Código departamento (Antioquia default)
                        "05001", # Código municipio (Medellín default)
                        "U"      # Zona (Urbana default)
                    ]
                    lineas_us.append(",".join(linea_us))
                    pacientes_procesados.add(paciente.id)

                # --- LÓGICA AF (FACTURAS) ---
                fecha_inicio = factura.fecha_inicio_periodo.strftime('%d/%m/%Y') if factura.fecha_inicio_periodo else factura.fecha_factura.strftime('%d/%m/%Y')
                fecha_final = factura.fecha_final_periodo.strftime('%d/%m/%Y') if factura.fecha_final_periodo else factura.fecha_factura.strftime('%d/%m/%Y')

                linea_af = [ 
                    "050012362501", 
                    "NOMBRE DE TU CLINICA SAS", 
                    "NI", 
                    "900123456-7", 
                    factura.numero_factura or '',
                    fecha_inicio,
                    fecha_final,
                    paciente.aseguradora or "EPS001", 
                    "NOMBRE EPS", 
                    "CONTRATO123", 
                    "PLANBENEFICIOS", 
                    "", # Número de póliza
                    str(int(factura.valor_copago or 0)), 
                    str(int(factura.valor_comision or 0)), 
                    str(int(factura.valor_descuentos or 0)), 
                    str(int(factura.valor_total or 0))
                ]
                lineas_af.append(",".join(linea_af))

                # --- PROCESAR CITAS Y PROCEDIMIENTOS DENTRO DE LA FACTURA ---
                for cita in factura.citas:
                    current_app.logger.debug(f"Procesando Cita ID: {cita.id} para Factura {factura.numero_factura}")

                    # --- LÓGICA AC (CONSULTAS) ---
                    fecha_cita_str = cita.fecha.strftime('%d/%m/%Y') if isinstance(cita.fecha, datetime) else cita.fecha.strftime('%d/%m/%Y')
                    
                    # Usamos el código de consulta de la cita, o un default si no existe
                    codigo_consulta = cita.codigo_consulta_cups or "890201" # 890201: Consulta de primera vez por odontología general

                    linea_ac = [ 
                        factura.numero_factura or '', 
                        "050012362501", 
                        paciente.tipo_documento or '', 
                        paciente.documento or '', 
                        fecha_cita_str, 
                        "", # Número de autorización
                        codigo_consulta, 
                        "10", # Finalidad (10=No aplica/Tratamiento) - Invisible Default
                        "13", # Causa externa (13=Enfermedad general) - Invisible Default
                        "K029", # Diagnóstico principal (Caries dentina) - Default temporal si no hay en cita
                        "", "", "", # Diagnósticos relacionados
                        "1", # Tipo de diagnóstico principal (1=Impresión diagnóstica)
                        str(int(factura.valor_total or 0)), # Valor consulta
                        str(int(factura.valor_cuota_moderadora or 0)), # Valor cuota moderadora
                        str(int(factura.valor_total or 0)) # Valor neto
                    ]
                    lineas_ac.append(",".join(linea_ac))

                    # --- LÓGICA AP (PROCEDIMIENTOS) ---
                    procedimientos_de_cita = list(cita.procedimientos)
                    current_app.logger.debug(f"    Cita {cita.id} tiene {len(procedimientos_de_cita)} procedimientos asociados.")

                    for procedimiento in procedimientos_de_cita:
                        current_app.logger.debug(f"      Procesando Procedimiento ID: {procedimiento.id}, CUPS: {procedimiento.codigo_cups}")
                        
                        fecha_procedimiento_str = cita.fecha.strftime('%d/%m/%Y')

                        linea_ap = [
                            factura.numero_factura or '',
                            "050012362501", # Código del prestador
                            paciente.tipo_documento or '',
                            paciente.documento or '',
                            fecha_procedimiento_str,
                            "", # Número de autorización
                            procedimiento.codigo_cups or '',
                            "1", # Ámbito de realización (ambulatorio)
                            "1", # Finalidad del procedimiento (diagnóstico)
                            "",  # Personal que atiende
                            procedimiento.diagnostico_cie10 or '',
                            "", # Diag. relacionado
                            "", # Complicación
                            "1", # Forma de realización (quirúrgico)
                            str(int(procedimiento.valor)) if procedimiento.valor is not None else "0"
                        ]
                        lineas_ap.append(",".join(linea_ap))

            # --- GENERAR CONTENIDOS Y ARCHIVO DE CONTROL (CT) ---
            contenido_af = "\n".join(lineas_af)
            contenido_us = "\n".join(lineas_us)
            contenido_ac = "\n".join(lineas_ac)
            contenido_ap = "\n".join(lineas_ap)

            codigo_prestador_ct = "050012362501"
            fecha_remision_ct = datetime.now(local_timezone).strftime('%d/%m/%Y')
            
            lineas_ct = []
            if lineas_af: lineas_ct.append(f"{codigo_prestador_ct},{fecha_remision_ct},AF,{len(lineas_af)}")
            if lineas_us: lineas_ct.append(f"{codigo_prestador_ct},{fecha_remision_ct},US,{len(lineas_us)}")
            if lineas_ac: lineas_ct.append(f"{codigo_prestador_ct},{fecha_remision_ct},AC,{len(lineas_ac)}")
            if lineas_ap: lineas_ct.append(f"{codigo_prestador_ct},{fecha_remision_ct},AP,{len(lineas_ap)}")
            contenido_ct = "\n".join(lineas_ct)

            # --- CREAR Y ENVIAR EL ZIP ---
            mem_zip = io.BytesIO()
            with zipfile.ZipFile(mem_zip, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
                if contenido_af: zf.writestr(f'AF{fecha_para_nombre_rips.strftime("%y%m")}.txt', contenido_af)
                if contenido_us: zf.writestr(f'US{fecha_para_nombre_rips.strftime("%y%m")}.txt', contenido_us)
                if contenido_ac: zf.writestr(f'AC{fecha_para_nombre_rips.strftime("%y%m")}.txt', contenido_ac)
                if contenido_ap: zf.writestr(f'AP{fecha_para_nombre_rips.strftime("%y%m")}.txt', contenido_ap)
                if contenido_ct: zf.writestr(f'CT{fecha_para_nombre_rips.strftime("%y%m")}.txt', contenido_ct)
            
            mem_zip.seek(0)
            nombre_archivo_zip = f"RIPS_{fecha_inicio_str}_a_{fecha_fin_str}.zip"
            return send_file(mem_zip, mimetype='application/zip', as_attachment=True, download_name=nombre_archivo_zip)

        except ValueError as ve:
            flash(f"Error de formato de fecha: {ve}. Asegúrate de usar mm/dd/yyyy en el formulario.", "danger")
            current_app.logger.error(f"Error de formato de fecha en RIPS: {ve}", exc_info=True)
        except Exception as e:
            flash(f"Ocurrió un error al generar los RIPS: {e}", "danger")
            current_app.logger.error(f"Error general al generar RIPS: {e}", exc_info=True)
            
    return render_template('reportes.html')