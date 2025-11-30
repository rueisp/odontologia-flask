"""
Script para migrar nombres y apellidos de pacientes existentes
a los campos separados requeridos para RIPS.

Este script toma los campos 'nombres' y 'apellidos' concatenados
y los divide en primer_nombre, segundo_nombre, primer_apellido, segundo_apellido.
"""
from clinica import create_app
from clinica.models import Paciente
from clinica.extensions import db

app = create_app()

def dividir_nombres(nombres_completos):
    """Divide nombres completos en primer y segundo nombre."""
    if not nombres_completos:
        return '', ''
    
    partes = nombres_completos.strip().split()
    if len(partes) == 0:
        return '', ''
    elif len(partes) == 1:
        return partes[0], ''
    else:
        # Primer nombre es la primera parte, el resto es segundo nombre
        return partes[0], ' '.join(partes[1:])

def dividir_apellidos(apellidos_completos):
    """Divide apellidos completos en primer y segundo apellido."""
    if not apellidos_completos:
        return '', ''
    
    partes = apellidos_completos.strip().split()
    if len(partes) == 0:
        return '', ''
    elif len(partes) == 1:
        return partes[0], ''
    else:
        # Primer apellido es la primera parte, el resto es segundo apellido
        return partes[0], ' '.join(partes[1:])

with app.app_context():
    print("Buscando pacientes con campos de nombre separados vacíos...")
    
    # Buscar pacientes que no tengan los campos separados
    pacientes_sin_separar = Paciente.query.filter(
        (Paciente.primer_nombre == None) | (Paciente.primer_nombre == ''),
        Paciente.is_deleted == False
    ).all()
    
    print(f"Encontrados {len(pacientes_sin_separar)} pacientes para actualizar.\n")
    
    actualizados = 0
    for paciente in pacientes_sin_separar:
        print(f"Procesando: {paciente.nombres} {paciente.apellidos} (Doc: {paciente.documento})")
        
        # Dividir nombres
        primer_nombre, segundo_nombre = dividir_nombres(paciente.nombres)
        primer_apellido, segundo_apellido = dividir_apellidos(paciente.apellidos)
        
        # Actualizar campos
        paciente.primer_nombre = primer_nombre
        paciente.segundo_nombre = segundo_nombre
        paciente.primer_apellido = primer_apellido
        paciente.segundo_apellido = segundo_apellido
        
        print(f"  → Primer nombre: {primer_nombre}")
        print(f"  → Segundo nombre: {segundo_nombre}")
        print(f"  → Primer apellido: {primer_apellido}")
        print(f"  → Segundo apellido: {segundo_apellido}\n")
        
        actualizados += 1
    
    # Guardar cambios
    if actualizados > 0:
        db.session.commit()
        print(f"✅ {actualizados} pacientes actualizados exitosamente!")
    else:
        print("No hay pacientes para actualizar.")
    
    # Verificar un paciente específico
    print("\n--- Verificación ---")
    p = Paciente.query.filter_by(documento='2002000203').first()
    if p:
        print(f"Paciente: {p.nombres} {p.apellidos}")
        print(f"Campos separados:")
        print(f"  Primer nombre: {p.primer_nombre}")
        print(f"  Segundo nombre: {p.segundo_nombre}")
        print(f"  Primer apellido: {p.primer_apellido}")
        print(f"  Segundo apellido: {p.segundo_apellido}")
