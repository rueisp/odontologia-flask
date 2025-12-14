# clinica/routes/export.py

# --- Importaciones Necesarias ---
from flask import Blueprint, send_file, request, render_template, current_app
from werkzeug.utils import secure_filename
from io import BytesIO
import pandas as pd
import os
from datetime import datetime, date
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
import re
import pytz 

# --- Importaciones de tus Modelos (AGREGAMOS EPS y Municipio) ---
from ..models import db, Paciente, Evolucion, EPS, Municipio

# --- Creación del Blueprint ---
export_bp = Blueprint('export', __name__)

# --- FUNCIÓN AUXILIAR PARA OBTENER NOMBRES REALES ---
def obtener_nombres_rips(paciente):
    """
    Busca los nombres reales de EPS, Municipio y Departamento 
    basado en los códigos del paciente. Retorna un diccionario.
    """
    # 1. Aseguradora (EPS)
    nombre_eps = paciente.aseguradora or 'No especificado'
    if paciente.codigo_aseguradora:
        cod_eps = str(paciente.codigo_aseguradora).strip()
        eps_obj = EPS.query.filter(EPS.codigo.ilike(cod_eps)).first()
        if eps_obj:
            nombre_eps = eps_obj.nombre
        # Si no lo encuentra, nos quedamos con lo que tenga paciente.aseguradora

    # 2. Municipio y Departamento
    nombre_muni = paciente.municipio or 'No especificado'
    nombre_depto = paciente.departamento or 'No especificado'

    if paciente.codigo_municipio and paciente.codigo_departamento:
        cod_mpio = str(paciente.codigo_municipio).strip()
        cod_dpto = str(paciente.codigo_departamento).strip()

        # Intento 1: Búsqueda exacta
        mpio_obj = Municipio.query.filter_by(codigo=cod_mpio).first()
        
        # Intento 2: Código corto
        if not mpio_obj and len(cod_mpio) > 2:
            cod_corto = cod_mpio[-3:] 
            mpio_obj = Municipio.query.filter_by(codigo=cod_corto, codigo_departamento=cod_dpto).first()

        if mpio_obj:
            nombre_muni = mpio_obj.nombre
            nombre_depto = mpio_obj.nombre_departamento

    return {
        'aseguradora': nombre_eps,
        'municipio': nombre_muni,
        'departamento': nombre_depto
    }


# --- Exportar a Excel (MEJORADO) ---
@export_bp.route('/exportar_excel/<int:id>')
def exportar_excel(id):
    paciente = Paciente.query.get_or_404(id)
    
    # Obtenemos los nombres bonitos
    nombres_rips = obtener_nombres_rips(paciente)

    datos = {"Campo": [], "Valor": []}
    campos = [ "id", "nombres", "apellidos", "tipo_documento", "documento", "fecha_nacimiento", "edad", "email", "telefono", "genero", "estado_civil", "direccion", "barrio", "municipio", "departamento", "aseguradora", "tipo_vinculacion", "ocupacion", "referido_por", "nombre_responsable", "telefono_responsable", "parentesco", "motivo_consulta", "enfermedad_actual", "antecedentes_personales", "antecedentes_familiares", "antecedentes_quirurgicos", "antecedentes_hemorragicos", "farmacologicos", "reaccion_medicamentos", "alergias", "habitos", "cepillado", "examen_fisico", "ultima_visita_odontologo", "plan_tratamiento", "observaciones"]
    
    for campo in campos:
        # Si el campo es uno de los que calculamos, usamos el valor calculado
        if campo in nombres_rips:
            valor = nombres_rips[campo]
        else:
            valor = getattr(paciente, campo, "")
            
        datos["Campo"].append(campo.replace("_", " ").capitalize())
        datos["Valor"].append(valor if valor else "No disponible")
        
    df = pd.DataFrame(datos)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Paciente')
    output.seek(0)
    return send_file(output, download_name=f"Paciente_{paciente.id}.xlsx", as_attachment=True)


# --- Exportar a Word (MEJORADO) ---
@export_bp.route('/exportar_word/<int:id>')
def exportar_word(id):
    paciente = Paciente.query.get_or_404(id)
    doc = Document()

    # Obtenemos los nombres bonitos para usarlos en la tabla
    nombres_rips = obtener_nombres_rips(paciente)

    # Estilo de fuente por defecto
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(8) 

    # Zona Horaria
    local_timezone = pytz.timezone('America/Bogota') 
    now_in_local_tz = datetime.now(local_timezone)

    # --- ENCABEZADO ---
    fecha_emision_formateada = now_in_local_tz.strftime('%d/%m/%Y %H:%M')
    p_fecha = doc.add_paragraph(f'Fecha de Emisión: {fecha_emision_formateada}')
    p_fecha.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for run in p_fecha.runs:
        run.font.size = Pt(7)
        run.italic = True

    titulo = doc.add_heading('Historia Clínica Odontológica', level=1)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER

    subtitulo = doc.add_paragraph()
    subtitulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_consultorio = subtitulo.add_run('Odontologia Dr. Rueis Pitre')
    font_consultorio = run_consultorio.font
    font_consultorio.name = 'Calibri'
    font_consultorio.size = Pt(10)
    font_consultorio.italic = True
    font_consultorio.bold = True

    doc.add_paragraph() 

    # --- DATOS DE FILIACIÓN (USANDO NOMBRES RIPS) ---
    doc.add_heading('1. Datos de Filiación', level=2)
    campos_filiacion = [
        ("Nombres", paciente.nombres), ("Apellidos", paciente.apellidos),
        ("Tipo Doc.", paciente.tipo_documento), ("Documento", paciente.documento),
        ("Fecha Nac.", paciente.fecha_nacimiento.strftime('%d/%m/%Y') if paciente.fecha_nacimiento else 'N/A'),
        ("Edad", paciente.edad),
        ("Email", paciente.email), ("Teléfono", paciente.telefono),
        ("Género", paciente.genero), ("Estado Civil", paciente.estado_civil),
        ("Dirección", paciente.direccion), ("Ocupación", paciente.ocupacion),
        # AQUÍ USAMOS LOS NOMBRES CALCULADOS:
        ("Municipio", nombres_rips['municipio']), ("Departamento", nombres_rips['departamento']),
        ("Aseguradora", nombres_rips['aseguradora']), ("Tipo Vinculación", paciente.tipo_vinculacion)
    ]
    crear_tabla_formato(doc, campos_filiacion, una_columna=False, label_font_size=Pt(7), value_font_size=Pt(7), vertical_align_top=True)
    doc.add_paragraph()

    # --- ANAMNESIS (Se mantiene igual) ---
    doc.add_heading('2. Anamnesis y Antecedentes', level=2)
    campos_anamnesis = [
        ("Motivo de Consulta", limpiar_texto_para_word(paciente.motivo_consulta)),
        ("Enfermedad Actual", limpiar_texto_para_word(paciente.enfermedad_actual)),
        ("Antec. Personales", limpiar_texto_para_word(paciente.antecedentes_personales)),
        ("Antec. Familiares", limpiar_texto_para_word(paciente.antecedentes_familiares)),
        ("Antec. Quirúrgicos", limpiar_texto_para_word(paciente.antecedentes_quirurgicos)),
        ("Antec. Hemorrágicos", limpiar_texto_para_word(paciente.antecedentes_hemorragicos)),
        ("Farmacológicos", limpiar_texto_para_word(paciente.farmacologicos)),
        ("Reacción a Med.", limpiar_texto_para_word(paciente.reaccion_medicamentos)),
        ("Alergias", limpiar_texto_para_word(paciente.alergias)),
        ("Hábitos", limpiar_texto_para_word(paciente.habitos)),
        ("Cepillado", limpiar_texto_para_word(paciente.cepillado)),
        ("Examen Físico", limpiar_texto_para_word(paciente.examen_fisico)),
        ("Última Visita Od.", limpiar_texto_para_word(paciente.ultima_visita_odontologo)),
        ("Plan de Tratamiento", limpiar_texto_para_word(paciente.plan_tratamiento)),
        ("Observaciones", limpiar_texto_para_word(paciente.observaciones))
    ]
    crear_tabla_formato(doc, campos_anamnesis, una_columna=False, label_font_size=Pt(7), value_font_size=Pt(7), vertical_align_top=True)
    doc.add_paragraph()

    # --- EVOLUCIÓN (Se mantiene la corrección de zona horaria) ---
    doc.add_heading('3. Evolución del Paciente', level=2)
    tabla_evos = doc.add_table(rows=1, cols=2)
    tabla_evos.style = 'Table Grid'
    tabla_evos.columns[0].width = Inches(1.25)
    tabla_evos.columns[1].width = Inches(5.25)
    hdr_cells = tabla_evos.rows[0].cells
    hdr_cells[0].text = 'Fecha'; hdr_cells[0].paragraphs[0].runs[0].bold = True
    hdr_cells[1].text = 'Descripción de la Evolución'; hdr_cells[1].paragraphs[0].runs[0].bold = True

    for evo in paciente.evoluciones.order_by(Evolucion.fecha.asc()):
        row_cells = tabla_evos.add_row().cells
        
        if evo.fecha.tzinfo is None: 
            fecha_evo_utc = evo.fecha.replace(tzinfo=pytz.utc)
        else: 
            fecha_evo_utc = evo.fecha

        fecha_evo_local = fecha_evo_utc.astimezone(local_timezone)
        row_cells[0].text = fecha_evo_local.strftime('%d/%m/%Y %H:%M') 
        row_cells[1].text = evo.descripcion

    output = BytesIO()
    doc.save(output)
    output.seek(0)
    download_filename = f"Historia_Clinica_{paciente.documento or paciente.id}.docx"
    return send_file(output, download_name=download_filename, as_attachment=True)


# --- FUNCIONES AUXILIARES (Sin cambios) ---

def limpiar_texto_para_word(texto):
    if texto is None: return ""
    texto = str(texto)
    texto = texto.replace('\r\n', ' ').replace('\n', ' ')
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

def crear_tabla_formato(doc, campos, una_columna=False, label_font_size=None, value_font_size=None, vertical_align_top=False):
    cols = 2 if una_columna else 4
    tabla = doc.add_table(rows=0, cols=cols)
    tabla.style = 'Table Grid'

    if una_columna:
        tabla.columns[0].width = Inches(1.8)
        tabla.columns[1].width = Inches(4.7)
    else: 
        tabla.columns[0].width = Inches(1.2)
        tabla.columns[1].width = Inches(2.1)
        tabla.columns[2].width = Inches(1.2)
        tabla.columns[3].width = Inches(2.1)

    from docx.enum.table import WD_ROW_HEIGHT_RULE, WD_ALIGN_VERTICAL
    paso = 1 if una_columna else 2
    for i in range(0, len(campos), paso):
        row_cells = tabla.add_row().cells
        if vertical_align_top:
            for cell in row_cells:
                cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP

        label_izq, value_izq = campos[i]
        p_label_izq = row_cells[0].paragraphs[0]
        run_label_izq = p_label_izq.add_run(f"{label_izq}:")
        run_label_izq.bold = True
        if label_font_size: run_label_izq.font.size = label_font_size

        p_value_izq = row_cells[1].paragraphs[0]
        run_value_izq = p_value_izq.add_run(str(value_izq) if value_izq is not None else 'N/A')
        if value_font_size: run_value_izq.font.size = value_font_size
        p_value_izq.paragraph_format.space_before = Pt(0)
        p_value_izq.paragraph_format.space_after = Pt(0)
        p_value_izq.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        p_value_izq.alignment = WD_ALIGN_PARAGRAPH.LEFT

        if not una_columna and i + 1 < len(campos):
            label_der, value_der = campos[i + 1]
            p_label_der = row_cells[2].paragraphs[0]
            run_label_der = p_label_der.add_run(f"{label_der}:")
            run_label_der.bold = True
            if label_font_size: run_label_der.font.size = label_font_size

            p_value_der = row_cells[3].paragraphs[0]
            run_value_der = p_value_der.add_run(str(value_der) if value_der is not None else 'N/A')
            if value_font_size: run_value_der.font.size = value_font_size
            p_value_der.paragraph_format.space_before = Pt(0)
            p_value_der.paragraph_format.space_after = Pt(0)
            p_value_der.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            p_value_der.alignment = WD_ALIGN_PARAGRAPH.LEFT

# --- FUNCIÓN AUXILIAR add_image_to_doc (se mantiene igual) ---
def add_image_to_doc(doc, ruta_relativa_db, width=3.0):
    """Añade una imagen directamente al documento si es una ruta local. Ignora URLs externas."""
    if ruta_relativa_db and not ruta_relativa_db.startswith(('http://', 'https://')):
        ruta_absoluta = os.path.join(current_app.root_path, 'static', ruta_relativa_db)
        if os.path.exists(ruta_absoluta):
            try:
                doc.add_picture(ruta_absoluta, width=Inches(width))
            except Exception as e:
                doc.add_paragraph(f"(Error al insertar imagen desde local: {e})")

# --- FUNCIÓN AUXILIAR add_image_to_cell (se mantiene igual) ---
def add_image_to_cell(cell, ruta_relativa_db, label, width=3.0):
    """Añade una etiqueta y una imagen dentro de una celda de tabla si es una ruta local. Ignora URLs externas."""
    cell.text = ''
    p = cell.add_paragraph()
    p.add_run(f"{label}:").bold = True

    if ruta_relativa_db and not ruta_relativa_db.startswith(('http://', 'https://')):
        ruta_absoluta = os.path.join(current_app.root_path, 'static', ruta_relativa_db)
        if os.path.exists(ruta_absoluta):
            try:
                cell.add_paragraph().add_run().add_picture(ruta_absoluta, width=Inches(width))
            except Exception as e:
                cell.add_paragraph(f"(Error al insertar imagen desde local en celda: {e})")