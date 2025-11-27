"""
Script para importar municipios principales de Colombia (códigos DIVIPOLA)
Ejecutar desde la raíz del proyecto: python importar_municipios.py
"""

from clinica import create_app
from clinica.extensions import db
from clinica.models import Municipio

# Municipios principales de Colombia con códigos DIVIPOLA
# Formato: (codigo_municipio, nombre_municipio, codigo_departamento, nombre_departamento)
MUNICIPIOS = [
    # Antioquia
    ("05001", "Medellín", "05", "Antioquia"),
    ("05002", "Abejorral", "05", "Antioquia"),
    ("05088", "Bello", "05", "Antioquia"),
    ("05129", "Caldas", "05", "Antioquia"),
    ("05266", "Envigado", "05", "Antioquia"),
    ("05360", "Itagüí", "05", "Antioquia"),
    ("05380", "La Estrella", "05", "Antioquia"),
    ("05631", "Rionegro", "05", "Antioquia"),
    ("05658", "Sabaneta", "05", "Antioquia"),
    
    # Atlántico
    ("08001", "Barranquilla", "08", "Atlántico"),
    ("08078", "Baranoa", "08", "Atlántico"),
    ("08137", "Campo de la Cruz", "08", "Atlántico"),
    ("08141", "Candelaria", "08", "Atlántico"),
    ("08296", "Galapa", "08", "Atlántico"),
    ("08421", "Malambo", "08", "Atlántico"),
    ("08520", "Palmar de Varela", "08", "Atlántico"),
    ("08558", "Polonuevo", "08", "Atlántico"),
    ("08560", "Ponedera", "08", "Atlántico"),
    ("08573", "Puerto Colombia", "08", "Atlántico"),
    ("08634", "Sabanagrande", "08", "Atlántico"),
    ("08638", "Sabanalarga", "08", "Atlántico"),
    ("08675", "Santa Lucía", "08", "Atlántico"),
    ("08685", "Santo Tomás", "08", "Atlántico"),
    ("08758", "Soledad", "08", "Atlántico"),
    
    # Bogotá D.C.
    ("11001", "Bogotá D.C.", "11", "Bogotá D.C."),
    
    # Bolívar
    ("13001", "Cartagena de Indias", "13", "Bolívar"),
    ("13430", "Magangué", "13", "Bolívar"),
    ("13244", "El Carmen de Bolívar", "13", "Bolívar"),
    ("13873", "Turbaco", "13", "Bolívar"),
    
    # Boyacá
    ("15001", "Tunja", "15", "Boyacá"),
    ("15176", "Duitama", "15", "Boyacá"),
    ("15759", "Sogamoso", "15", "Boyacá"),
    ("15238", "Chiquinquirá", "15", "Boyacá"),
    
    # Caldas
    ("17001", "Manizales", "17", "Caldas"),
    ("17380", "La Dorada", "17", "Caldas"),
    ("17486", "Chinchiná", "17", "Caldas"),
    
    # Caquetá
    ("18001", "Florencia", "18", "Caquetá"),
    ("18247", "San Vicente del Caguán", "18", "Caquetá"),
    
    # Casanare
    ("85001", "Yopal", "85", "Casanare"),
    ("85010", "Aguazul", "85", "Casanare"),
    ("85015", "Villanueva", "85", "Casanare"),
    
    # Cauca
    ("19001", "Popayán", "19", "Cauca"),
    ("19622", "Santander de Quilichao", "19", "Cauca"),
    
    # Cesar
    ("20001", "Valledupar", "20", "Cesar"),
    ("20045", "Aguachica", "20", "Cesar"),
    
    # Chocó
    ("27001", "Quibdó", "27", "Chocó"),
    
    # Córdoba
    ("23001", "Montería", "23", "Córdoba"),
    ("23162", "Cereté", "23", "Córdoba"),
    ("23464", "Lorica", "23", "Córdoba"),
    ("23466", "Montelíbano", "23", "Córdoba"),
    ("23670", "Sahagún", "23", "Córdoba"),
    
    # Cundinamarca
    ("25001", "Agua de Dios", "25", "Cundinamarca"),
    ("25126", "Cajicá", "25", "Cundinamarca"),
    ("25148", "Chía", "25", "Cundinamarca"),
    ("25175", "Cota", "25", "Cundinamarca"),
    ("25214", "Facatativá", "25", "Cundinamarca"),
    ("25245", "Funza", "25", "Cundinamarca"),
    ("25269", "Girardot", "25", "Cundinamarca"),
    ("25286", "Madrid", "25", "Cundinamarca"),
    ("25295", "Mosquera", "25", "Cundinamarca"),
    ("25328", "Zipaquirá", "25", "Cundinamarca"),
    ("25430", "Soacha", "25", "Cundinamarca"),
    ("25473", "Fusagasugá", "25", "Cundinamarca"),
    
    # Huila
    ("41001", "Neiva", "41", "Huila"),
    ("41244", "Garzón", "41", "Huila"),
    ("41357", "La Plata", "41", "Huila"),
    ("41551", "Pitalito", "41", "Huila"),
    
    # La Guajira
    ("44001", "Riohacha", "44", "La Guajira"),
    ("44430", "Maicao", "44", "La Guajira"),
    
    # Magdalena
    ("47001", "Santa Marta", "47", "Magdalena"),
    ("47189", "Ciénaga", "47", "Magdalena"),
    
    # Meta
    ("50001", "Villavicencio", "50", "Meta"),
    ("50006", "Acacías", "50", "Meta"),
    ("50226", "Granada", "50", "Meta"),
    
    # Nariño
    ("52001", "Pasto", "52", "Nariño"),
    ("52356", "Ipiales", "52", "Nariño"),
    ("52835", "Tumaco", "52", "Nariño"),
    
    # Norte de Santander
    ("54001", "Cúcuta", "54", "Norte de Santander"),
    ("54498", "Ocaña", "54", "Norte de Santander"),
    ("54874", "Villa del Rosario", "54", "Norte de Santander"),
    
    # Putumayo
    ("86001", "Mocoa", "86", "Putumayo"),
    
    # Quindío
    ("63001", "Armenia", "63", "Quindío"),
    ("63190", "Calarcá", "63", "Quindío"),
    ("63470", "Montenegro", "63", "Quindío"),
    
    # Risaralda
    ("66001", "Pereira", "66", "Risaralda"),
    ("66170", "Dosquebradas", "66", "Risaralda"),
    ("66318", "La Virginia", "66", "Risaralda"),
    ("66400", "Santa Rosa de Cabal", "66", "Risaralda"),
    
    # Santander
    ("68001", "Bucaramanga", "68", "Santander"),
    ("68051", "Barrancabermeja", "68", "Santander"),
    ("68081", "Barbosa", "68", "Santander"),
    ("68092", "Floridablanca", "68", "Santander"),
    ("68276", "Girón", "68", "Santander"),
    ("68547", "Piedecuesta", "68", "Santander"),
    
    # Sucre
    ("70001", "Sincelejo", "70", "Sucre"),
    
    # Tolima
    ("73001", "Ibagué", "73", "Tolima"),
    ("73268", "Espinal", "73", "Tolima"),
    
    # Valle del Cauca
    ("76001", "Cali", "76", "Valle del Cauca"),
    ("76111", "Buenaventura", "76", "Valle del Cauca"),
    ("76109", "Buga", "76", "Valle del Cauca"),
    ("76126", "Candelaria", "76", "Valle del Cauca"),
    ("76147", "Cartago", "76", "Valle del Cauca"),
    ("76364", "Jamundí", "76", "Valle del Cauca"),
    ("76520", "Palmira", "76", "Valle del Cauca"),
    ("76834", "Tuluá", "76", "Valle del Cauca"),
    ("76890", "Yumbo", "76", "Valle del Cauca"),
    
    # Vaupés
    ("97001", "Mitú", "97", "Vaupés"),
    
    # Vichada
    ("99001", "Puerto Carreño", "99", "Vichada"),
]

def importar_municipios():
    """Importa municipios principales de Colombia a la base de datos"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("📥 IMPORTANDO MUNICIPIOS DE COLOMBIA (DIVIPOLA)")
        print("=" * 60)
        print()
        
        try:
            # Preguntar si eliminar existentes
            respuesta = input("⚠️  ¿Deseas eliminar los municipios existentes antes de importar? (s/n): ")
            if respuesta.lower() == 's':
                Municipio.query.delete()
                db.session.commit()
                print("🗑️  Municipios existentes eliminados")
                print()
            
            # Importar municipios
            print(f"⏳ Importando {len(MUNICIPIOS)} municipios principales...")
            total_importados = 0
            errores = 0
            
            for codigo, nombre, codigo_depto, nombre_depto in MUNICIPIOS:
                try:
                    # Verificar si existe
                    existe = Municipio.query.filter_by(codigo=codigo).first()
                    
                    if existe:
                        # Actualizar
                        existe.nombre = nombre
                        existe.codigo_departamento = codigo_depto
                        existe.nombre_departamento = nombre_depto
                    else:
                        # Crear nuevo
                        nuevo_municipio = Municipio(
                            codigo=codigo,
                            nombre=nombre,
                            codigo_departamento=codigo_depto,
                            nombre_departamento=nombre_depto
                        )
                        db.session.add(nuevo_municipio)
                    
                    total_importados += 1
                    
                    # Commit cada 30
                    if total_importados % 30 == 0:
                        db.session.commit()
                        print(f"  ✅ Importados {total_importados} municipios...")
                
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
            total_en_bd = Municipio.query.count()
            print(f"🔍 Total de municipios en la base de datos: {total_en_bd}")
            print()
            
            # Mostrar por departamento
            print("📋 Municipios por departamento:")
            departamentos = db.session.query(
                Municipio.nombre_departamento, 
                db.func.count(Municipio.id)
            ).group_by(Municipio.nombre_departamento).order_by(Municipio.nombre_departamento).all()
            
            for depto, count in departamentos:
                print(f"   {depto}: {count} municipios")
            
        except Exception as e:
            db.session.rollback()
            print()
            print("=" * 60)
            print("❌ ERROR EN LA IMPORTACIÓN")
            print("=" * 60)
            print(f"Error: {str(e)}")
            raise

if __name__ == "__main__":
    importar_municipios()