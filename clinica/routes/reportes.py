# clinica/routes/reportes.py

from flask import Blueprint, render_template, request, flash, send_file, current_app
from flask_login import login_required
from datetime import datetime, time, timedelta
import io
import zipfile
import pytz

# --- IMPORTACIONES ---
from ..extensions import db
from ..models import Factura, Cita, Paciente, Procedimiento
from sqlalchemy.orm import joinedload
# Importamos la nueva función de limpieza
from ..utils import limpiar_texto_rips

reportes_bp = Blueprint('reportes', __name__)

# ==============================================================================
# CONFIGURACIÓN DEL PRESTADOR (EDITA ESTO CON TUS DATOS REALES)
# ==============================================================================
DATOS_PRESTADOR = {
    "codigo_habilitacion": "050012362501",  # TU CÓDIGO DE 12 DÍGITOS
    "nit": "900123456-7",                   # TU NIT
    "nombre": "CLINICA ODONTOLOGICA SAS"    # TU RAZÓN SOCIAL
}

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
            # Configuración de zona horaria
            local_timezone = pytz.timezone('America/Bogota')

            # Conversión de fechas (Vienen en MM/DD/YYYY desde el JS del frontend)
            fecha_inicio_local_date = datetime.strptime(fecha_inicio_str, '%m/%d/%Y').date()
            fecha_fin_local_date = datetime.strptime(fecha_fin_str, '%m/%d/%Y').date()

            # Calcular rangos UTC para la consulta SQL
            rango_inicio_utc = local_timezone.localize(datetime.combine(fecha_inicio_local_date, time.min)).astimezone(pytz.utc)
            rango_fin_siguiente_dia_local = fecha_fin_local_date + timedelta(days=1)
            rango_fin_utc = local_timezone.localize(datetime.combine(rango_fin_siguiente_dia_local, time.min)).astimezone(pytz.utc)

            # --- CONSULTA DE FACTURAS (CON EAGER LOADING) ---
            facturas_en_periodo = Factura.query.options(
                joinedload(Factura.paciente),
                joinedload(Factura.citas).joinedload(Cita.procedimientos)
            ).filter(
                Factura.fecha_factura >= rango_inicio_utc,
                Factura.fecha_factura < rango_fin_utc
            ).order_by(Factura.fecha_factura.desc()).all()

            if not facturas_en_periodo:
                flash('No se encontraron facturas generadas en el período seleccionado.', 'warning')
                return render_template('reportes.html')

            # --- PREPARACIÓN DE LISTAS ---
            lineas_af = [] # Transacciones
            lineas_us = [] # Usuarios
            lineas_ac = [] # Consultas
            lineas_ap = [] # Procedimientos
            
            pacientes_procesados = set() # Evitar duplicar usuarios en el archivo US
            
            # Formato de fecha para el nombre del archivo (DDMMAAAA)
            fecha_nombre_archivo = datetime.now(local_timezone).strftime("%d%m%Y")

            # ==================================================================
            # ITERACIÓN PRINCIPAL
            # ==================================================================
            for factura in facturas_en_periodo:
                paciente = factura.paciente
                if not paciente: continue

                # Calculamos edad actual
                edad = (datetime.now().date() - paciente.fecha_nacimiento).days // 365 if paciente.fecha_nacimiento else 0

                # ----------------------------------------------------------
                # 1. GENERACIÓN ARCHIVO US (USUARIOS)
                # ----------------------------------------------------------
                if paciente.id not in pacientes_procesados:
                    
                    # 1. Definir variables auxiliares
                    unidad_medida = "1" 
                    
                    # --- LÓGICA GEOGRÁFICA BLINDADA ---
                    # Primero decidimos el municipio (Dato Real o Default)
                    mpio_final = paciente.codigo_municipio if paciente.codigo_municipio else "05001"
                    
                    # El departamento OBLIGATORIAMENTE son los 2 primeros dígitos de ese municipio
                    # Así garantizamos que si sale 05001, el depto sea 05. Si sale 15001, sea 15.
                    depto_final = mpio_final[:2]

                    linea_us = [
                        paciente.tipo_documento_rips or '',
                        paciente.documento or '',
                        limpiar_texto_rips(paciente.codigo_aseguradora or paciente.aseguradora, 6),
                        str(paciente.tipo_usuario_rips or '1'),
                        limpiar_texto_rips(paciente.primer_apellido),
                        limpiar_texto_rips(paciente.segundo_apellido),
                        limpiar_texto_rips(paciente.primer_nombre),
                        limpiar_texto_rips(paciente.segundo_nombre),
                        str(edad),
                        unidad_medida,
                        paciente.genero_rips or paciente.get_genero_rips() or "M", 
                        depto_final,  # <--- Usamos la variable calculada
                        mpio_final,   # <--- Usamos la variable calculada
                        paciente.zona_residencia or "U"
                    ]
                    lineas_us.append(",".join(linea_us))
                    pacientes_procesados.add(paciente.id)

                    
                # ----------------------------------------------------------
                # 2. GENERACIÓN ARCHIVO AF (FACTURACIÓN)
                # ----------------------------------------------------------
                f_inicio = factura.fecha_inicio_periodo.strftime('%d/%m/%Y') if factura.fecha_inicio_periodo else factura.fecha_factura.strftime('%d/%m/%Y')
                f_fin = factura.fecha_final_periodo.strftime('%d/%m/%Y') if factura.fecha_final_periodo else factura.fecha_factura.strftime('%d/%m/%Y')

                # --- LÓGICA DE SEGURIDAD (CORREGIDA): CALCULAR SIEMPRE ---
                # No confiamos en factura.valor_total guardado, porque el usuario pudo editar
                # el precio del procedimiento después de crear la factura.
                # Calculamos la suma real en este momento exacto.
                
                suma_procedimientos = 0
                for c in factura.citas:
                    for p in c.procedimientos:
                        suma_procedimientos += (p.valor or 0)
                
                # El valor total será la suma fresca de los procedimientos
                valor_total_reporte = suma_procedimientos
                
                # Si por alguna razón la suma dio 0 (raro), intentamos usar el guardado como fallback
                if valor_total_reporte == 0 and factura.valor_total:
                     valor_total_reporte = factura.valor_total

                linea_af = [
                    DATOS_PRESTADOR["codigo_habilitacion"],
                    limpiar_texto_rips(DATOS_PRESTADOR["nombre"]),
                    "NI", 
                    DATOS_PRESTADOR["nit"],
                    limpiar_texto_rips(factura.numero_factura),
                    f_inicio,
                    f_fin,
                    limpiar_texto_rips(paciente.codigo_aseguradora or paciente.aseguradora, 6),
                    limpiar_texto_rips(paciente.aseguradora), 
                    "", 
                    "", 
                    "", 
                    str(int(factura.valor_copago or 0)),
                    str(int(factura.valor_comision or 0)),
                    str(int(factura.valor_descuentos or 0)),
                    str(int(valor_total_reporte)) # <--- USAMOS EL VALOR RECALCULADO SIEMPRE
                ]
                lineas_af.append(",".join(linea_af))

                # ----------------------------------------------------------
                # 3. PROCESAMIENTO DE CITAS (CONSULTAS - AC) Y PROCEDIMIENTOS (AP)
                # ----------------------------------------------------------
                for cita in factura.citas:
                    fecha_cita_str = cita.fecha.strftime('%d/%m/%Y')

                    # --- ARCHIVO AC (CONSULTAS) ---
                    # Solo generamos línea AC si la cita tiene código de consulta
                    # Y NO es solo un procedimiento puro (aunque en odontología a veces se mezclan)
                    if cita.codigo_consulta_cups:
                        linea_ac = [
                            limpiar_texto_rips(factura.numero_factura),
                            DATOS_PRESTADOR["codigo_habilitacion"],
                            paciente.tipo_documento_rips or '',
                            paciente.documento or '',
                            fecha_cita_str,
                            "", # Número Autorización
                            cita.codigo_consulta_cups,
                            cita.finalidad_consulta or "10", # Usamos dato real o default
                            cita.causa_externa or "13",      # Usamos dato real o default
                            cita.diagnostico_principal or "K029", # Diagnóstico CIE10
                            cita.diagnostico_relacionado1 or "",
                            cita.diagnostico_relacionado2 or "",
                            cita.diagnostico_relacionado3 or "",
                            cita.tipo_diagnostico_principal or "1",
                            str(int(valor_total_reporte or 0)), # Valor consulta
                            str(int(factura.valor_cuota_moderadora or 0)),
                            str(int(valor_total_reporte or 0))  # Valor neto
                        ]
                        lineas_ac.append(",".join(linea_ac))

                    # --- ARCHIVO AP (PROCEDIMIENTOS) ---
                    for proc in cita.procedimientos:
                        
                        # 1. LÓGICA DE CORRECCIÓN DE DIAGNÓSTICO (FIX CIE10)
                        # Obtenemos el diagnóstico o usamos K029 por defecto
                        dx_principal = proc.diagnostico_cie10 or "K029"
                        dx_principal = dx_principal.strip() # Quitamos espacios
                        
                        # Si el código tiene solo 3 letras (Ej: "K02"), le agregamos un "9" al final -> "K029"
                        # Esto evita el rechazo por longitud inválida.
                        if len(dx_principal) == 3:
                            dx_principal += "9"

                        linea_ap = [
                            limpiar_texto_rips(factura.numero_factura),
                            DATOS_PRESTADOR["codigo_habilitacion"],
                            paciente.tipo_documento_rips or '',
                            paciente.documento or '',
                            fecha_cita_str,
                            "", # Número Autorización
                            proc.codigo_cups or '',
                            "1", # Ámbito (1=Ambulatorio)
                            "1", # Finalidad (1=Diagnóstico/Terapéutico)
                            "",  # Personal que atiende
                            dx_principal, # <--- AQUÍ USAMOS LA VARIABLE CORREGIDA
                            "",  # Diag Relacionado
                            "",  # Complicación
                            "1", # Forma realización (1=Directa)
                            str(int(proc.valor or 0))
                        ]
                        lineas_ap.append(",".join(linea_ap))

            # ==================================================================
            # GENERACIÓN ARCHIVO CT (CONTROL)
            # ==================================================================
            lineas_ct = []
            fecha_remision = datetime.now(local_timezone).strftime('%d/%m/%Y')
            
            if lineas_af: lineas_ct.append(f"{DATOS_PRESTADOR['codigo_habilitacion']},{fecha_remision},AF{fecha_nombre_archivo},{len(lineas_af)}")
            if lineas_us: lineas_ct.append(f"{DATOS_PRESTADOR['codigo_habilitacion']},{fecha_remision},US{fecha_nombre_archivo},{len(lineas_us)}")
            if lineas_ac: lineas_ct.append(f"{DATOS_PRESTADOR['codigo_habilitacion']},{fecha_remision},AC{fecha_nombre_archivo},{len(lineas_ac)}")
            if lineas_ap: lineas_ct.append(f"{DATOS_PRESTADOR['codigo_habilitacion']},{fecha_remision},AP{fecha_nombre_archivo},{len(lineas_ap)}")

            contenido_ct = "\n".join(lineas_ct)

            # ==================================================================
            # CREACIÓN DEL ZIP
            # ==================================================================
            mem_zip = io.BytesIO()
            with zipfile.ZipFile(mem_zip, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
                if lineas_af: zf.writestr(f'AF{fecha_nombre_archivo}.txt', "\n".join(lineas_af))
                if lineas_us: zf.writestr(f'US{fecha_nombre_archivo}.txt', "\n".join(lineas_us))
                if lineas_ac: zf.writestr(f'AC{fecha_nombre_archivo}.txt', "\n".join(lineas_ac))
                if lineas_ap: zf.writestr(f'AP{fecha_nombre_archivo}.txt', "\n".join(lineas_ap))
                if contenido_ct: zf.writestr(f'CT{fecha_nombre_archivo}.txt', contenido_ct)
            
            mem_zip.seek(0)
            nombre_zip = f"RIPS_{fecha_inicio_str.replace('/','-')}_al_{fecha_fin_str.replace('/','-')}.zip"
            
            return send_file(mem_zip, mimetype='application/zip', as_attachment=True, download_name=nombre_zip)

        except ValueError as ve:
            flash(f"Error de formato de fecha. Asegúrate de usar mm/dd/yyyy.", "danger")
            current_app.logger.error(f"Error RIPS Fecha: {ve}")
        except Exception as e:
            flash(f"Error al generar RIPS: {e}", "danger")
            current_app.logger.error(f"Error RIPS General: {e}", exc_info=True)
            
    return render_template('reportes.html')