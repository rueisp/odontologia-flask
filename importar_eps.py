"""
Script para importar códigos de EPS a la base de datos
Ejecutar desde la raíz del proyecto: python importar_eps.py
"""

from clinica import create_app
from clinica.extensions import db
from clinica.models import EPS

# Códigos oficiales de EPS en Colombia (actualizados 2024)
CODIGOS_EPS = [
    # EPS principales del Régimen Contributivo
    ("EPS002", "Salud Total S.A. E.P.S.", True),
    ("EPS005", "E.P.S. Sanitas S.A.", True),
    ("EPS013", "Compensar E.P.S.", True),
    ("EPS014", "EPS y Medicina Prepagada Suramericana S.A.", True),
    ("EPS015", "Coomeva E.P.S. S.A.", True),
    ("EPS016", "Famisanar E.P.S. - Cafam - Colsubsidio", True),
    ("EPS017", "Servicio Occidental de Salud S.O.S. S.A.", True),
    ("EPS020", "Salud MIA E.P.S. S.A.S.", True),
    ("EPS037", "Nueva EPS S.A.", True),
    
    # EPS Régimen Subsidiado
    ("ESS002", "Asmet Salud E.S.S.", True),
    ("ESS003", "Ecoopsos E.S.S.", True),
    ("ESS024", "Capital Salud E.P.S.-S", True),
    ("ESS033", "Coosalud E.S.S.", True),
    ("ESS089", "Savia Salud E.P.S.", True),
    ("ESS092", "Cajacopi Atlántico E.P.S.", True),
    ("ESS119", "Comfachocó E.P.S.-S", True),
    ("ESS124", "Comfacor E.P.S.", True),
    ("ESS204", "Mutual Ser E.S.S.", True),
    ("ESS208", "Anas Wayuu E.P.S.I.", True),
    ("ESS209", "Mallamas E.P.S.I.", True),
    ("ESS233", "Pijaos Salud E.P.S.I.", True),
    
    # Cajas de Compensación Familiar (CCF) que prestan servicios de salud
    ("CCFC01", "Comfenalco Valle E.P.S.", True),
    ("CCFC07", "Comfamiliar Risaralda E.P.S.", True),
    ("CCFC16", "Comfamiliar Huila E.P.S.", True),
    ("CCFC20", "Comfachocó E.P.S.-S", True),
    ("CCFC25", "Capresoca E.P.S.", True),
    ("CCFC33", "EPS Familiar de Colombia", True),
    ("CCFC50", "Comfaoriente E.P.S.-S", True),
    
    # Regímenes Especiales
    ("EPSC01", "Fondo de Pasivo Social de Ferrocarriles", True),
    ("EPSC03", "Magisterio", True),
    ("EPSC04", "Universidad de Antioquia", True),
    ("EPSC05", "Universidad Nacional", True),
    ("EPSC16", "Ecopetrol", True),
    
    # EPS Indígenas (EPSI)
    ("EPSIC1", "Dusakawi E.P.S.I.", True),
    ("EPSIC2", "Manexka E.P.S.I.", True),
    ("EPSIC3", "Pijaos Salud E.P.S.I.", True),
    
    # Medicina Prepagada (para referencia)
    ("EMP002", "Cafesalud Medicina Prepagada S.A.", True),
    ("EMP023", "Compañía de Medicina Prepagada Colsanitas S.A.", True),
    ("EMP028", "Salud Coomeva Medicina Prepagada S.A.", True),
    
    # EPS históricas (algunas en liquidación - mantener para registros históricos)
    ("EPS001", "Salud Colmena E.P.S. S.A.", False),
    ("EPS003", "Cafesalud E.P.S. S.A.", False),
    ("EPS004", "Bonsalud (En Liquidación)", False),
    ("EPS024", "Cajanal EPS (Fusionada)", False),
    ("EPS025", "Capresoca EPS", True),
    ("EPS027", "Barranquilla Sana E.P.S. (En Liquidación)", False),
    ("EPS028", "Calisalud E.P.S.", False),
    ("EPS029", "E.P.S. de Caldas S.A.", False),
    ("EPS030", "E.P.S. Cóndor S.A.", False),
    ("EPS031", "Selvasalud S.A. E.P.S.", False),
    ("EPS032", "Metropolitana de Salud EPS (En Liquidación)", False),
    ("EPS033", "Saludvida EPS S.A.", True),
    ("EPS034", "Medimás EPS S.A.S.", True),
]

def importar_eps():
    """Importa códigos de EPS a la base de datos"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("📥 IMPORTANDO CÓDIGOS DE EPS")
        print("=" * 60)
        print()
        
        try:
            # Preguntar si eliminar existentes
            respuesta = input("⚠️  ¿Deseas eliminar los códigos de EPS existentes antes de importar? (s/n): ")
            if respuesta.lower() == 's':
                EPS.query.delete()
                db.session.commit()
                print("🗑️  Códigos existentes eliminados")
                print()
            
            # Importar códigos
            print(f"⏳ Importando {len(CODIGOS_EPS)} códigos de EPS...")
            total_importados = 0
            errores = 0
            
            for codigo, nombre, activa in CODIGOS_EPS:
                try:
                    # Verificar si existe
                    existe = EPS.query.filter_by(codigo=codigo).first()
                    
                    if existe:
                        # Actualizar
                        existe.nombre = nombre
                        existe.activa = activa
                    else:
                        # Crear nuevo
                        nuevo_eps = EPS(
                            codigo=codigo,
                            nombre=nombre,
                            activa=activa
                        )
                        db.session.add(nuevo_eps)
                    
                    total_importados += 1
                    
                    # Commit cada 20
                    if total_importados % 20 == 0:
                        db.session.commit()
                        print(f"  ✅ Importadas {total_importados} EPS...")
                
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
            print(f"📊 Total importadas: {total_importados}")
            print(f"⚠️  Errores: {errores}")
            print()
            
            # Verificar
            total_en_bd = EPS.query.count()
            print(f"🔍 Total de EPS en la base de datos: {total_en_bd}")
            print()
            
            # Mostrar estadísticas
            activas = EPS.query.filter_by(activa=True).count()
            inactivas = EPS.query.filter_by(activa=False).count()
            
            print("📋 Estadísticas:")
            print(f"   EPS Activas: {activas}")
            print(f"   EPS Inactivas/En liquidación: {inactivas}")
            print()
            
            print("💡 Nota: Las EPS inactivas se mantienen para registros históricos")
            
        except Exception as e:
            db.session.rollback()
            print()
            print("=" * 60)
            print("❌ ERROR EN LA IMPORTACIÓN")
            print("=" * 60)
            print(f"Error: {str(e)}")
            raise

if __name__ == "__main__":
    importar_eps()