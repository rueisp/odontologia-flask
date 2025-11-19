# clinica/routes/procedimientos.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

# Importamos las herramientas y modelos necesarios
from ..extensions import db
from ..models import Procedimiento, Cita

# Creamos el Blueprint para estas rutas
procedimientos_bp = Blueprint('procedimientos', __name__)


@procedimientos_bp.route('/cita/<int:cita_id>/registrar-procedimiento', methods=['GET', 'POST'])
@login_required
def registrar_procedimiento(cita_id):
    """
    Muestra el formulario para registrar un nuevo procedimiento en una cita
    y maneja el guardado de los datos.
    """
    # Buscamos la cita a la que pertenece este procedimiento. Si no existe, da error 404.
    cita = Cita.query.get_or_404(cita_id)

    # TODO: Aquí puedes añadir una verificación de permisos si es necesario
    # (ej. que el usuario actual sea el doctor de la cita)

    if request.method == 'POST':
        # 1. Obtenemos los datos del formulario
        codigo_cups = request.form.get('codigo_cups')
        diagnostico_cie10 = request.form.get('diagnostico_cie10')
        descripcion = request.form.get('descripcion')
        valor_str = request.form.get('valor')

        # 2. Validamos los datos
        if not codigo_cups or not diagnostico_cie10 or not valor_str:
            flash('El Código CUPS, Diagnóstico CIE-10 y el Valor son campos obligatorios.', 'danger')
            # Re-renderizamos el formulario con los datos que ya había ingresado
            return render_template('registrar_procedimiento.html', cita=cita, form_data=request.form)

        try:
            valor = float(valor_str)
        except ValueError:
            flash('El valor del procedimiento debe ser un número válido.', 'danger')
            return render_template('registrar_procedimiento.html', cita=cita, form_data=request.form)
            
        try:
            # 3. Creamos el nuevo objeto Procedimiento
            nuevo_procedimiento = Procedimiento(
                cita_id=cita.id,
                codigo_cups=codigo_cups,
                diagnostico_cie10=diagnostico_cie10,
                descripcion=descripcion,
                valor=valor
            )
            
            # 4. Guardamos en la base de datos
            db.session.add(nuevo_procedimiento)
            db.session.commit()
            
            flash('Procedimiento registrado exitosamente.', 'success')
            
            # 5. Redirigimos al usuario de vuelta a la página de editar la cita
            #    para que pueda ver el procedimiento que acaba de añadir.
            return redirect(url_for('calendario.editar_cita', cita_id=cita.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error al guardar el procedimiento: {e}', 'danger')

    # Si es un método GET, simplemente mostramos el formulario
    return render_template('registrar_procedimiento.html', cita=cita, form_data={})