"""
Script para importar códigos CUPS desde Excel a la base de datos
Ejecutar desde la raíz del proyecto: python importar_cups.py
"""

import pandas as pd
from clinica import create_app
from clinica.extensions import db
from clinica.models import CUPSCode

def importar_cups_desde_excel(ruta_excel):
    """
    Importa códigos CUPS desde un archivo Excel
    
    Args:
        ruta_excel: Ruta al archivo Excel con los códigos CUPS
    """
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("📥 IMPORTANDO CÓDIGOS CUPS DESDE EXCEL")
        print("=" * 60)
        print()
        
        try:
            # Leer el archivo Excel
            print(f"📂 Leyendo archivo: {ruta_excel}")
            df = pd.read_excel(ruta_excel)
            
            print(f"✅ Archivo leído correctamente")
            print(f"📊 Total de filas: {len(df)}")
            print()
            
            # Mostrar las primeras columnas para verificar
            print("🔍 Columnas detectadas:")
            for i, col in enumerate(df.columns):
                print(f"  {i}: {col}")
            print()
            
            # Ajusta estos índices según las columnas de tu Excel
            # En tu caso: Columna B = código, Columna C = descripción
            columna_codigo = 1  # Ajustar si es necesario
            columna_descripcion = 2  # Ajustar si es necesario
            
            # Si las columnas tienen nombres diferentes, puedes usar índices:
            # columna_codigo = df.columns[1]  # Columna B (índice 1)
            # columna_descripcion = df.columns[2]  # Columna C (índice 2)
            
            print(f"🔧 Usando columnas:")
            print(f"   Código: {columna_codigo}")
            print(f"   Descripción: {columna_descripcion}")
            print()
            
            # Limpiar la tabla antes de importar (opcional)
            respuesta = input("⚠️  ¿Deseas eliminar los códigos CUPS existentes antes de importar? (s/n): ")
            if respuesta.lower() == 's':
                CUPSCode.query.delete()
                db.session.commit()
                print("🗑️  Códigos existentes eliminados")
                print()
            
            # Importar códigos
            print("⏳ Importando códigos...")
            total_importados = 0
            errores = 0
            
            for index, row in df.iterrows():
                try:
                    codigo = str(row[columna_codigo]).strip()
                    descripcion = str(row.iloc[columna_descripcion]).strip()
                    
                    # Saltar filas vacías
                    if pd.isna(codigo) or codigo == '' or codigo == 'nan':
                        continue
                    
                    # Verificar si el código ya existe
                    existe = CUPSCode.query.filter_by(code=codigo).first()
                    
                    if existe:
                        # Actualizar el existente
                        existe.description = descripcion
                    else:
                        # Crear nuevo
                        nuevo_cups = CUPSCode(
                            code=codigo,
                            description=descripcion
                        )
                        db.session.add(nuevo_cups)
                    
                    total_importados += 1
                    
                    # Commit cada 50 registros para evitar problemas de memoria
                    if total_importados % 50 == 0:
                        db.session.commit()
                        print(f"  ✅ Importados {total_importados} códigos...")
                
                except Exception as e:
                    errores += 1
                    print(f"  ⚠️  Error en fila {index + 2}: {e}")
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
            
            # Verificar cantidad en la base de datos
            total_en_bd = CUPSCode.query.count()
            print(f"🔍 Total de códigos CUPS en la base de datos: {total_en_bd}")
            
        except FileNotFoundError:
            print("❌ ERROR: No se encontró el archivo Excel")
            print(f"   Ruta buscada: {ruta_excel}")
            print()
            print("💡 Asegúrate de que:")
            print("   1. El archivo existe en esa ubicación")
            print("   2. La ruta es correcta")
            print("   3. Tienes permisos de lectura")
        
        except Exception as e:
            db.session.rollback()
            print()
            print("=" * 60)
            print("❌ ERROR EN LA IMPORTACIÓN")
            print("=" * 60)
            print(f"Error: {str(e)}")
            print()
            print("La base de datos no fue modificada")
            raise

if __name__ == "__main__":
    print()
    print("🔧 CONFIGURACIÓN DE IMPORTACIÓN")
    print()
    
    # IMPORTANTE: Cambia esta ruta por la ubicación de tu archivo Excel
    ruta_archivo = input("Ingresa la ruta completa de tu archivo Excel: ").strip()
    
    # Ejemplo: C:\\Users\\rueis\\Documents\\Tabla_CUPS_RIPS.xlsx
    # O si está en la carpeta del proyecto: ./Tabla_CUPS_RIPS.xlsx
    
    if not ruta_archivo:
        print("❌ No ingresaste ninguna ruta")
    else:
        importar_cups_desde_excel(ruta_archivo)