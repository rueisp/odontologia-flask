# import_cups.py
import pandas as pd
from clinica import create_app, db # Ajusta según cómo inicies tu app
from clinica.models import CUPSCode # Importa el nuevo modelo

def import_cups_data(excel_file_path):
    app = create_app()
    with app.app_context():
        try:
            df = pd.read_excel(excel_file_path)
            # Ajusta 'Código' y 'Nombre' si tus columnas en Excel se llaman diferente
            df = df[['Código', 'Nombre']].drop_duplicates(subset=['Código'])

            print(f"Importando {len(df)} códigos CUPS...")
            for index, row in df.iterrows():
                code = str(row['Código']).strip()
                description = str(row['Nombre']).strip()

                existing_code = CUPSCode.query.filter_by(code=code).first()
                if not existing_code:
                    new_cups = CUPSCode(code=code, description=description)
                    db.session.add(new_cups)
                # else: opcional: actualizar descripción si cambia

            db.session.commit()
            print("Importación de códigos CUPS completada.")
        except Exception as e:
            db.session.rollback()
            print(f"Error durante la importación de CUPS: {e}")

if __name__ == '__main__':
    # Reemplaza con la ruta de tu archivo Excel de CUPS
    import_cups_data('tu_archivo_cups.xlsx')