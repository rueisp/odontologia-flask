"""
Script para importar códigos CIE-10 de odontología a la base de datos
Ejecutar desde la raíz del proyecto: python importar_cie10.py
"""

from clinica import create_app
from clinica.extensions import db
from clinica.models import CIE10

# Códigos CIE-10 más comunes en odontología (K00-K14)
CODIGOS_CIE10 = [
    # K00 - Trastornos del desarrollo y de la erupción de los dientes
    ("K00", "Trastornos del desarrollo y de la erupción de los dientes", "Desarrollo dental"),
    ("K000", "Anodoncia", "Desarrollo dental"),
    ("K001", "Dientes supernumerarios", "Desarrollo dental"),
    ("K002", "Anomalías del tamaño y de la forma del diente", "Desarrollo dental"),
    ("K003", "Dientes moteados", "Desarrollo dental"),
    ("K004", "Alteraciones en la formación dentaria", "Desarrollo dental"),
    ("K005", "Alteraciones hereditarias de la estructura dentaria", "Desarrollo dental"),
    ("K006", "Alteraciones en la erupción dentaria", "Desarrollo dental"),
    ("K007", "Síndrome de la erupción dentaria", "Desarrollo dental"),
    ("K008", "Otros trastornos del desarrollo de los dientes", "Desarrollo dental"),
    ("K009", "Trastorno del desarrollo de los dientes, no especificado", "Desarrollo dental"),
    
    # K01 - Dientes incluidos e impactados
    ("K01", "Dientes incluidos e impactados", "Inclusión dental"),
    ("K010", "Dientes incluidos", "Inclusión dental"),
    ("K011", "Dientes impactados", "Inclusión dental"),
    
    # K02 - Caries dental
    ("K02", "Caries dental", "Caries"),
    ("K020", "Caries limitada al esmalte", "Caries"),
    ("K021", "Caries de la dentina", "Caries"),
    ("K022", "Caries del cemento", "Caries"),
    ("K023", "Caries dentaria detenida", "Caries"),
    ("K024", "Odontoclasia", "Caries"),
    ("K028", "Otras caries dentales", "Caries"),
    ("K029", "Caries dental, no especificada", "Caries"),
    
    # K03 - Otras enfermedades de los tejidos duros de los dientes
    ("K03", "Otras enfermedades de los tejidos duros de los dientes", "Tejidos duros"),
    ("K030", "Atrición excesiva de los dientes", "Tejidos duros"),
    ("K031", "Abrasión de los dientes", "Tejidos duros"),
    ("K032", "Erosión de los dientes", "Tejidos duros"),
    ("K033", "Resorción patológica de los dientes", "Tejidos duros"),
    ("K034", "Hipercementosis", "Tejidos duros"),
    ("K035", "Anquilosis dental", "Tejidos duros"),
    ("K036", "Depósitos [acreciones] en los dientes", "Tejidos duros"),
    ("K037", "Cambios posteruptivos del color de los tejidos dentales duros", "Tejidos duros"),
    ("K038", "Otras enfermedades especificadas de los tejidos duros de los dientes", "Tejidos duros"),
    ("K039", "Enfermedad no especificada de los tejidos duros de los dientes", "Tejidos duros"),
    
    # K04 - Enfermedades de la pulpa y de los tejidos periapicales
    ("K04", "Enfermedades de la pulpa y de los tejidos periapicales", "Endodoncia"),
    ("K040", "Pulpitis", "Endodoncia"),
    ("K041", "Necrosis de la pulpa", "Endodoncia"),
    ("K042", "Degeneración de la pulpa", "Endodoncia"),
    ("K043", "Formación anormal de tejido duro en la pulpa", "Endodoncia"),
    ("K044", "Periodontitis apical aguda originada en la pulpa", "Endodoncia"),
    ("K045", "Periodontitis apical crónica", "Endodoncia"),
    ("K046", "Absceso periapical con fístula", "Endodoncia"),
    ("K047", "Absceso periapical sin fístula", "Endodoncia"),
    ("K048", "Quiste radicular", "Endodoncia"),
    ("K049", "Otras enfermedades y las no especificadas de la pulpa y del tejido periapical", "Endodoncia"),
    
    # K05 - Gingivitis y enfermedades periodontales
    ("K05", "Gingivitis y enfermedades periodontales", "Periodoncia"),
    ("K050", "Gingivitis aguda", "Periodoncia"),
    ("K051", "Gingivitis crónica", "Periodoncia"),
    ("K052", "Periodontitis aguda", "Periodoncia"),
    ("K053", "Periodontitis crónica", "Periodoncia"),
    ("K054", "Periodontosis", "Periodoncia"),
    ("K055", "Otras enfermedades periodontales", "Periodoncia"),
    ("K056", "Enfermedad periodontal, no especificada", "Periodoncia"),
    
    # K06 - Otros trastornos de la encía y de la zona edéntula
    ("K06", "Otros trastornos de la encía y de la zona edéntula", "Encía"),
    ("K060", "Retracción gingival", "Encía"),
    ("K061", "Hiperplasia gingival", "Encía"),
    ("K062", "Lesiones de la encía y de la zona edéntula asociadas con traumatismo", "Encía"),
    ("K068", "Otros trastornos especificados de la encía y de la zona edéntula", "Encía"),
    ("K069", "Trastorno no especificado de la encía y de la zona edéntula", "Encía"),
    
    # K07 - Anomalías dentofaciales
    ("K07", "Anomalías dentofaciales [incluso maloclusión]", "Ortodoncia"),
    ("K070", "Anomalías del tamaño de los maxilares", "Ortodoncia"),
    ("K071", "Anomalías de la relación maxilobasilar", "Ortodoncia"),
    ("K072", "Anomalías de la relación entre los arcos dentarios", "Ortodoncia"),
    ("K073", "Anomalías de la posición del diente", "Ortodoncia"),
    ("K074", "Maloclusión, tipo no especificado", "Ortodoncia"),
    ("K075", "Anomalías dentofaciales funcionales", "Ortodoncia"),
    ("K076", "Trastornos de la articulación temporomandibular", "Ortodoncia"),
    ("K078", "Otras anomalías dentofaciales", "Ortodoncia"),
    ("K079", "Anomalía dentofacial, no especificada", "Ortodoncia"),
    
    # K08 - Otros trastornos de los dientes y de sus estructuras de sostén
    ("K08", "Otros trastornos de los dientes y de sus estructuras de sostén", "Otros"),
    ("K080", "Exfoliación de los dientes debida a causas sistémicas", "Otros"),
    ("K081", "Pérdida de dientes debida a accidente, extracción o enfermedad periodontal local", "Otros"),
    ("K082", "Atrofia del reborde alveolar desdentado", "Otros"),
    ("K083", "Raíz dental retenida", "Otros"),
    ("K088", "Otros trastornos especificados de los dientes y de sus estructuras de sostén", "Otros"),
    ("K089", "Trastorno de los dientes y de sus estructuras de sostén, no especificado", "Otros"),
    
    # K09 - Quistes de la región bucal
    ("K09", "Quistes de la región bucal, no clasificados en otra parte", "Quistes"),
    ("K090", "Quistes originados por el desarrollo de los dientes", "Quistes"),
    ("K091", "Quistes de las fisuras (no odontogénicos)", "Quistes"),
    ("K092", "Otros quistes de los maxilares", "Quistes"),
    ("K098", "Otros quistes de la región bucal, no clasificados en otra parte", "Quistes"),
    ("K099", "Quiste de la región bucal, sin otra especificación", "Quistes"),
    
    # K10 - Otras enfermedades de los maxilares
    ("K10", "Otras enfermedades de los maxilares", "Maxilares"),
    ("K100", "Trastornos del desarrollo de los maxilares", "Maxilares"),
    ("K101", "Granuloma central de células gigantes", "Maxilares"),
    ("K102", "Afecciones inflamatorias de los maxilares", "Maxilares"),
    ("K103", "Alveolitis del maxilar", "Maxilares"),
    ("K108", "Otras enfermedades especificadas de los maxilares", "Maxilares"),
    ("K109", "Enfermedad de los maxilares, no especificada", "Maxilares"),
    
    # K11 - Enfermedades de las glándulas salivales
    ("K11", "Enfermedades de las glándulas salivales", "Glándulas salivales"),
    ("K110", "Atrofia de glándula salival", "Glándulas salivales"),
    ("K111", "Hipertrofia de glándula salival", "Glándulas salivales"),
    ("K112", "Sialadenitis", "Glándulas salivales"),
    ("K113", "Absceso de glándula salival", "Glándulas salivales"),
    ("K114", "Fístula de glándula salival", "Glándulas salivales"),
    ("K115", "Sialolitiasis", "Glándulas salivales"),
    ("K116", "Mucocele de glándula salival", "Glándulas salivales"),
    ("K117", "Alteraciones de la secreción salival", "Glándulas salivales"),
    ("K118", "Otras enfermedades de las glándulas salivales", "Glándulas salivales"),
    ("K119", "Enfermedad de glándula salival, no especificada", "Glándulas salivales"),
    
    # K12 - Estomatitis y lesiones afines
    ("K12", "Estomatitis y lesiones afines", "Mucosa bucal"),
    ("K120", "Estomatitis aftosa recurrente", "Mucosa bucal"),
    ("K121", "Otras formas de estomatitis", "Mucosa bucal"),
    ("K122", "Celulitis y absceso de boca", "Mucosa bucal"),
    
    # K13 - Otras enfermedades de los labios y de la mucosa bucal
    ("K13", "Otras enfermedades de los labios y de la mucosa bucal", "Mucosa bucal"),
    ("K130", "Enfermedades de los labios", "Mucosa bucal"),
    ("K131", "Mordedura del labio y de la mejilla", "Mucosa bucal"),
    ("K132", "Leucoplasia y otras alteraciones del epitelio bucal", "Mucosa bucal"),
    ("K133", "Leucoplasia pilosa", "Mucosa bucal"),
    ("K134", "Granuloma y lesiones semejantes de la mucosa bucal", "Mucosa bucal"),
    ("K135", "Fibrosis de la submucosa bucal", "Mucosa bucal"),
    ("K136", "Hiperplasia irritativa de la mucosa bucal", "Mucosa bucal"),
    ("K137", "Otras lesiones y las no especificadas de la mucosa bucal", "Mucosa bucal"),
    
    # K14 - Enfermedades de la lengua
    ("K14", "Enfermedades de la lengua", "Lengua"),
    ("K140", "Glositis", "Lengua"),
    ("K141", "Lengua geográfica", "Lengua"),
    ("K142", "Glositis romboidea mediana", "Lengua"),
    ("K143", "Hipertrofia de las papilas linguales", "Lengua"),
    ("K144", "Atrofia de las papilas linguales", "Lengua"),
    ("K145", "Lengua plegada", "Lengua"),
    ("K146", "Glosodinia", "Lengua"),
    ("K148", "Otras enfermedades de la lengua", "Lengua"),
    ("K149", "Enfermedad de la lengua, no especificada", "Lengua"),
    
    # Códigos adicionales importantes
    ("Z012", "Examen odontológico", "Prevención"),
    ("S025", "Fractura de los dientes", "Traumatismo"),
    ("S032", "Luxación del diente", "Traumatismo"),
]

def importar_cie10():
    """Importa códigos CIE-10 odontológicos a la base de datos"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("📥 IMPORTANDO CÓDIGOS CIE-10 ODONTOLÓGICOS")
        print("=" * 60)
        print()
        
        try:
            # Preguntar si eliminar existentes
            respuesta = input("⚠️  ¿Deseas eliminar los códigos CIE-10 existentes antes de importar? (s/n): ")
            if respuesta.lower() == 's':
                CIE10.query.delete()
                db.session.commit()
                print("🗑️  Códigos existentes eliminados")
                print()
            
            # Importar códigos
            print(f"⏳ Importando {len(CODIGOS_CIE10)} códigos CIE-10...")
            total_importados = 0
            errores = 0
            
            for codigo, descripcion, categoria in CODIGOS_CIE10:
                try:
                    # Verificar si existe
                    existe = CIE10.query.filter_by(codigo=codigo).first()
                    
                    if existe:
                        # Actualizar
                        existe.descripcion = descripcion
                        existe.categoria = categoria
                    else:
                        # Crear nuevo
                        nuevo_cie10 = CIE10(
                            codigo=codigo,
                            descripcion=descripcion,
                            categoria=categoria
                        )
                        db.session.add(nuevo_cie10)
                    
                    total_importados += 1
                    
                    # Commit cada 50
                    if total_importados % 50 == 0:
                        db.session.commit()
                        print(f"  ✅ Importados {total_importados} códigos...")
                
                except Exception as e:
                    errores += 1
                    print(f"  ⚠️  Error con código {codigo}: {e}")
                    continue
            
            # Commit final
            db.session.commit()
            
            print()
            print("=" * 60)
            print("✅ IMPORTACIÓN COMPLETADA")
            print("=" * 60)
            print(f"📊 Total importados: {total_importados}")
            print(f"⚠️  Errores: {errores}")
            print()
            
            # Verificar
            total_en_bd = CIE10.query.count()
            print(f"🔍 Total de códigos CIE-10 en la base de datos: {total_en_bd}")
            print()
            
            # Mostrar por categorías
            print("📋 Códigos por categoría:")
            categorias = db.session.query(CIE10.categoria, db.func.count(CIE10.id)).group_by(CIE10.categoria).all()
            for cat, count in categorias:
                print(f"   {cat}: {count} códigos")
            
        except Exception as e:
            db.session.rollback()
            print()
            print("=" * 60)
            print("❌ ERROR EN LA IMPORTACIÓN")
            print("=" * 60)
            print(f"Error: {str(e)}")
            raise

if __name__ == "__main__":
    importar_cie10()