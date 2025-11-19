# clinica/routes/reportes.py

from flask import Blueprint, render_template, request, flash, send_file, current_app # Añade current_app
from flask_login import login_required
from datetime import datetime, time, timedelta
import io
import zipfile
import pytz # ¡NECESARIO para zonas horarias!

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
            # Define la zona horaria local (igual que en main.py para consistencia)
            local_timezone = pytz.timezone('America/Bogota') # <--- AJUSTA SI ES DIFERENTE

            # 1. Convertir las cadenas de fecha a objetos date locales (como el usuario las ve)
            fecha_inicio_local_date = datetime.strptime(fecha_inicio_str, '%m/%d/%Y').date()
            fecha_fin_local_date = datetime.strptime(fecha_fin_str, '%m/%d/%Y').date()

            # --- CORRECCIÓN CLAVE: Calcular los límites UTC exactos para la consulta ---
            # Calcular el inicio del rango en UTC (inclusive)
            # Combina la fecha de inicio local con la hora mínima, localiza y convierte a UTC.
            rango_inicio_utc = local_timezone.localize(datetime.combine(fecha_inicio_local_date, time.min)).astimezone(pytz.utc)
            
            # Calcular el fin del rango en UTC (exclusivo)
            # Esto representa el inicio del día siguiente al último día seleccionado localmente,
            # convertido a UTC. Usamos '<' en la consulta para incluir todo el último día.
            rango_fin_siguiente_dia_local = fecha_fin_local_date + timedelta(days=1)
            rango_fin_utc = local_timezone.localize(datetime.combine(rango_fin_siguiente_dia_local, time.min)).astimezone(pytz.utc)

            # --- LA CONSULTA CLAVE CORREGIDA ---
            # Comparamos Factura.fecha_factura (si es db.DateTime y guarda UTC) con objetos datetime UTC.
            facturas_en_periodo = Factura.query.filter(
                Factura.fecha_factura >= rango_inicio_utc,
                Factura.fecha_factura < rango_fin_utc      # ¡IMPORTANTE: Usar '<' para el límite superior exclusivo!
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

            # Para los nombres de archivo RIPS (AFYYMM.txt, etc.), usamos la fecha de inicio local
            # Convertimos a datetime para compatibilidad con strftime
            fecha_para_nombre_rips = datetime.combine(fecha_inicio_local_date, time.min)

            # --- PROCESAR CADA FACTURA ---
            for factura in facturas_en_periodo:
                paciente = factura.paciente
                if not paciente: 
                    current_app.logger.warning(f"Factura {factura.id} sin paciente asociado, se omite.")
                    continue

                # --- CORRECCIÓN 3: La lógica de USUARIOS (US) DEBE IR DENTRO del bucle de factura
                # Y bajo la condición de que el paciente no se haya procesado antes.
                if paciente.id not in pacientes_procesados:
                    edad = (datetime.now().date() - paciente.fecha_nacimiento).days // 365 if paciente.fecha_nacimiento else 0
                    
                    nombres_split = (paciente.nombres or '').split(' ', 1)
                    apellidos_split = (paciente.apellidos or '').split(' ', 1)

                    nombre1 = nombres_split[0] if nombres_split else ''
                    nombre2 = nombres_split[1] if len(nombres_split) > 1 else ''
                    
                    apellido1 = apellidos_split[0] if apellidos_split else ''
                    apellido2 = apellidos_split[1] if len(apellidos_split) > 1 else ''

                    linea_us = [
                        paciente.tipo_documento or '', # Asegura string vacío si es None
                        paciente.documento or '',
                        paciente.aseguradora if paciente.aseguradora and paciente.aseguradora.strip() else "EPS001",
                        "1",
                        apellido1,
                        apellido2,
                        nombre1,
                        nombre2,
                        str(edad),
                        "1" if paciente.genero == 'Masculino' else "2",
                        "05",
                        "05001",
                        "U"
                    ]
                    lineas_us.append(",".join(linea_us))
                    pacientes_procesados.add(paciente.id) # Añade al paciente después de procesarlo

                # TODO: (Mejora futura) Calcular el valor total de la factura sumando los procedimientos.
                # valor_real_factura = sum(proc.valor for cita in factura.citas for proc in cita.procedimientos)
                # factura.valor_total = valor_real_factura # Esto requeriría db.session.commit() para guardarse
                # Por ahora, usamos el valor que tenga la factura.
                
                # --- Construir línea AF (Facturas) ---
                linea_af = [ 
                    "050012362501", 
                    "NOMBRE DE TU CLINICA SAS", 
                    "NI", 
                    "900123456-7", 
                    factura.numero_factura or '', # Asegura que no sea None
                    factura.fecha_factura.strftime('%d/%m/%Y'), # Usa fecha_creacion
                    factura.fecha_factura.strftime('%d/%m/%Y'), # Usa fecha_creacion
                    paciente.aseguradora or "EPS001", 
                    "NOMBRE EPS", 
                    "CONTRATO123", 
                    "PLANBENEFICIOS", 
                    "", 
                    "0", "0", "0", 
                    str(int(factura.valor_total)) if factura.valor_total is not None else "0" # Maneja valor_total None
                ]
                lineas_af.append(",".join(linea_af))

                # --- PROCESAR CITAS Y PROCEDIMIENTOS DENTRO DE LA FACTURA ---
                for cita in factura.citas:
                    current_app.logger.debug(f"Procesando Cita ID: {cita.id} para Factura {factura.numero_factura}") # <-- AÑADIR ESTA LÍNEA

                    # Siempre se genera una línea de Consulta (AC) por cada cita.
                    # Asegura que cita.fecha sea datetime, si es un date, usa datetime.combine(cita.fecha, time.min)
                    fecha_cita_str = cita.fecha.strftime('%d/%m/%Y') if isinstance(cita.fecha, datetime) else cita.fecha.strftime('%d/%m/%Y')
                    linea_ac = [ factura.numero_factura or '', "050012362501", paciente.tipo_documento or '', paciente.documento or '', fecha_cita_str, "", "890203", "10", "13", "K029", "", "", "", "1", "0", "0", "0" ]
                    lineas_ac.append(",".join(linea_ac))
                    current_app.logger.debug(f"  AC line generated for Cita {cita.id}.") # <-- AÑADIR ESTA LÍNEA

                    # =======================================================
                # ▼▼▼ ¡LA NUEVA LÓGICA MÁGICA ESTÁ AQUÍ! ▼▼▼
                # =======================================================
                # Ahora, por cada procedimiento DENTRO de la cita, generamos una línea AP.
                # ANTES DEL BUCLE DE PROCEDIMIENTOS:
                # Convierte la colección dinámica a una lista para poder obtener su longitud y asegurar su carga
                procedimientos_de_cita = list(cita.procedimientos) # <-- CAMBIO CLAVE AQUÍ: Fuerza la carga y convierte a lista
                current_app.logger.debug(f"    Cita {cita.id} tiene {len(procedimientos_de_cita)} procedimientos asociados.") # <-- AÑADIR ESTA LÍNEA

                for procedimiento in procedimientos_de_cita: # <-- MODIFICADO: Itera sobre la lista cargada
                    current_app.logger.debug(f"      Procesando Procedimiento ID: {procedimiento.id}, CUPS: {procedimiento.codigo_cups}") # <-- AÑADIR ESTA LÍNEA
                    
                    # NOTA: En tu modelo Procedimiento, no hay un campo 'fecha'.
                    # La fecha del procedimiento siempre será la de la cita asociada.
                    # Por lo tanto, puedes simplificar la siguiente línea:
                    # fecha_procedimiento_str = procedimiento.fecha.strftime('%d/%m/%Y') if hasattr(procedimiento, 'fecha') and procedimiento.fecha else cita.fecha.strftime('%d/%m/%Y')
                    fecha_procedimiento_str = cita.fecha.strftime('%d/%m/%Y') # <-- SIMPLIFICADO

                    linea_ap = [
                        factura.numero_factura or '',
                        "050012362501", # Código del prestador
                        paciente.tipo_documento or '',
                        paciente.documento or '',
                        fecha_procedimiento_str, # Usamos la fecha de la cita
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
                    current_app.logger.debug(f"      Línea AP generada para Procedimiento {procedimiento.id}. Total AP líneas: {len(lineas_ap)}") # <-- AÑADIR ESTA LÍNEA
                # =======================================================
                # ▲▲▲ FIN DE LA NUEVA LÓGICA ▲▲▲
                # =======================================================

            # --- GENERAR CONTENIDOS Y ARCHIVO DE CONTROL (CT) ---
            contenido_af = "\n".join(lineas_af)
            contenido_us = "\n".join(lineas_us)
            contenido_ac = "\n".join(lineas_ac)
            contenido_ap = "\n".join(lineas_ap)

            codigo_prestador_ct = "050012362501"
            fecha_remision_ct = datetime.now(local_timezone).strftime('%d/%m/%Y') # Usa la zona horaria local
            
            lineas_ct = []
            if lineas_af: lineas_ct.append(f"{codigo_prestador_ct},{fecha_remision_ct},AF,{len(lineas_af)}")
            if lineas_us: lineas_ct.append(f"{codigo_prestador_ct},{fecha_remision_ct},US,{len(lineas_us)}")
            if lineas_ac: lineas_ct.append(f"{codigo_prestador_ct},{fecha_remision_ct},AC,{len(lineas_ac)}")
            if lineas_ap: lineas_ct.append(f"{codigo_prestador_ct},{fecha_remision_ct},AP,{len(lineas_ap)}")
            contenido_ct = "\n".join(lineas_ct)

                # --- CREAR Y ENVIAR EL ZIP ---
            mem_zip = io.BytesIO()
            with zipfile.ZipFile(mem_zip, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
                if contenido_af: zf.writestr(f'AF{fecha_para_nombre_rips.strftime("%y%m")}.txt', contenido_af) # CAMBIADO
                if contenido_us: zf.writestr(f'US{fecha_para_nombre_rips.strftime("%y%m")}.txt', contenido_us) # CAMBIADO
                if contenido_ac: zf.writestr(f'AC{fecha_para_nombre_rips.strftime("%y%m")}.txt', contenido_ac) # CAMBIADO
                if contenido_ap: zf.writestr(f'AP{fecha_para_nombre_rips.strftime("%y%m")}.txt', contenido_ap) # CAMBIADO
                if contenido_ct: zf.writestr(f'CT{fecha_para_nombre_rips.strftime("%y%m")}.txt', contenido_ct) # CAMBIADO
            
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