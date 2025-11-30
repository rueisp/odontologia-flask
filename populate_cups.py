"""
Script to populate CUPS codes table with common dental procedures
"""
from clinica import create_app
from clinica.models import CUPSCode
from clinica.extensions import db

app = create_app()

# Common dental CUPS codes (Colombia)
dental_cups_codes = [
    # Consultas
    ("890201", "Consulta de primera vez por odontología general"),
    ("890202", "Consulta de primera vez por odontología especializada"),
    ("890203", "Consulta de control por odontología general"),
    ("890204", "Consulta de control por odontología especializada"),
    
    # Prevención
    ("997101", "Control de placa bacteriana"),
    ("997102", "Aplicación de sellantes"),
    ("997103", "Aplicación de flúor"),
    ("997104", "Detartraje supragingival"),
    ("997105", "Profilaxis"),
    
    # Operatoria
    ("237101", "Obturación en amalgama"),
    ("237102", "Obturación en resina"),
    ("237103", "Reconstrucción de ángulo"),
    ("237104", "Reconstrucción de borde incisal"),
    
    # Endodoncia
    ("233101", "Pulpotomía"),
    ("233102", "Pulpectomía"),
    ("233103", "Tratamiento de conductos radiculares unirradicular"),
    ("233104", "Tratamiento de conductos radiculares birradicular"),
    ("233105", "Tratamiento de conductos radiculares multirradicular"),
    
    # Cirugía
    ("237201", "Exodoncia de diente temporal"),
    ("237202", "Exodoncia de diente permanente"),
    ("237203", "Exodoncia de diente incluido o retenido"),
    ("237204", "Alveoloplastia"),
    ("237205", "Frenectomía"),
    
    # Periodoncia
    ("237301", "Raspaje y alisado radicular por cuadrante"),
    ("237302", "Gingivectomía"),
    ("237303", "Gingivoplastia"),
    ("237304", "Cirugía periodontal a colgajo"),
    
    # Rehabilitación
    ("237401", "Corona provisional"),
    ("237402", "Corona en metal porcelana"),
    ("237403", "Corona en porcelana"),
    ("237404", "Prótesis total superior"),
    ("237405", "Prótesis total inferior"),
    ("237406", "Prótesis parcial removible"),
    
    # Ortodoncia
    ("237501", "Aparatología fija"),
    ("237502", "Aparatología removible"),
    ("237503", "Mantenedor de espacio"),
    
    # Radiología
    ("877101", "Radiografía periapical"),
    ("877102", "Radiografía oclusal"),
    ("877103", "Radiografía panorámica"),
    ("877104", "Radiografía cefalométrica"),
]

with app.app_context():
    print("Populating CUPS codes...")
    
    for code, description in dental_cups_codes:
        cups = CUPSCode(code=code, description=description)
        db.session.add(cups)
    
    db.session.commit()
    print(f"Successfully added {len(dental_cups_codes)} CUPS codes!")
    
    # Verify
    count = CUPSCode.query.count()
    print(f"Total CUPS codes in database: {count}")
    
    # Show first 5
    print("\nFirst 5 CUPS codes:")
    for cups in CUPSCode.query.limit(5).all():
        print(f"  {cups.code} - {cups.description}")
