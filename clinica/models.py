from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin 
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db

class Paciente(db.Model):
    __tablename__ = 'paciente' # Es buena práctica definir explícitamente el nombre de la tabla

    id = db.Column(db.Integer, primary_key=True)
    nombres = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    tipo_documento = db.Column(db.String(50), nullable=True) # Permitir NULL
    documento = db.Column(db.String(50), unique=True, nullable=True) # Permitir NULL, pero si existe debe ser único
    fecha_nacimiento = db.Column(db.Date, nullable=True) # Permitir NULL
    edad = db.Column(db.Integer, nullable=True)
    email = db.Column(db.String(100), nullable=True)
    telefono = db.Column(db.String(50), nullable=False) # Asumimos que teléfono es obligatorio
    genero = db.Column(db.String(50), nullable=True)
    estado_civil = db.Column(db.String(50), nullable=True)
    direccion = db.Column(db.String(200), nullable=True)
    barrio = db.Column(db.String(100), nullable=True)
    municipio = db.Column(db.String(100), nullable=True)
    departamento = db.Column(db.String(100), nullable=True)
    aseguradora = db.Column(db.String(100), nullable=True)
    tipo_vinculacion = db.Column(db.String(50), nullable=True)
    ocupacion = db.Column(db.String(100), nullable=True)
    referido_por = db.Column(db.String(100), nullable=True)
    nombre_responsable = db.Column(db.String(100), nullable=True)
    telefono_responsable = db.Column(db.String(50), nullable=True)
    parentesco = db.Column(db.String(50), nullable=True)
    motivo_consulta = db.Column(db.Text, nullable=True)
    enfermedad_actual = db.Column(db.Text, nullable=True)
    antecedentes_personales = db.Column(db.Text, nullable=True)
    antecedentes_familiares = db.Column(db.Text, nullable=True)
    antecedentes_quirurgicos = db.Column(db.Text, nullable=True)
    antecedentes_hemorragicos = db.Column(db.Text, nullable=True)
    farmacologicos = db.Column(db.Text, nullable=True)
    reaccion_medicamentos = db.Column(db.Text, nullable=True)
    alergias = db.Column(db.Text, nullable=True)
    habitos = db.Column(db.Text, nullable=True)
    cepillado = db.Column(db.Text, nullable=True)
    examen_fisico = db.Column(db.Text, nullable=True)
    ultima_visita_odontologo = db.Column(db.Text, nullable=True)
    plan_tratamiento = db.Column(db.Text, nullable=True)
    observaciones = db.Column(db.Text, nullable=True)
    imagen_1 = db.Column(db.String(200), nullable=True)
    imagen_2 = db.Column(db.String(200), nullable=True)
    dentigrama_canvas = db.Column(db.String(255), nullable=True)
    odontologo_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    odontologo = db.relationship('Usuario', back_populates='pacientes')
    imagen_perfil_url = db.Column(db.String(255), nullable=True) # Nuevo campo para la URL de la imagen de perfil
    # --- CAMPOS PARA SOFT DELETE ---
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    # --- FIN CAMPOS SOFT DELETE ---

    # Relaciones:
    # Para soft delete, la cascada a nivel de DB con 'delete-orphan' o 'ondelete=CASCADE'
    # no se activará como se espera. El borrado en cascada de relacionados (soft delete)
    # deberá manejarse en la lógica de la aplicación si es necesario.
    evoluciones = db.relationship('Evolucion', backref='paciente', lazy='dynamic') # cascade removido temporalmente
    # La relación con Citas se define a través del backref en el modelo Cita.
    # Si Paciente.citas existe por el backref de Cita.paciente, está bien.

class Evolucion(db.Model):
    __tablename__ = 'evolucion' # Buena práctica

    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=False) # ondelete='CASCADE' no tiene efecto con soft delete del padre
    
    # --- OPCIONAL: CAMPOS PARA SOFT DELETE EN EVOLUCION (si quieres que se puedan borrar evoluciones individualmente) ---
    # is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    # deleted_at = db.Column(db.DateTime, nullable=True)
    # --- FIN CAMPOS SOFT DELETE ---
    
class Cita(db.Model):
    __tablename__ = 'cita'

    id = db.Column(db.Integer, primary_key=True)
    # --- ¡RESTABLECIDA LA LÍNEA paciente_id! Y es nullable=True ---
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=True) 

    # --- ¡MODIFICACIÓN FINAL AQUÍ! ---
    paciente_nombres_str = db.Column(db.String(100), nullable=False, default='Paciente sin registrar') 
    paciente_apellidos_str = db.Column(db.String(100), nullable=False, default='') 
    # --- FIN MODIFICACIÓN FINAL ---
    paciente_telefono_str = db.Column(db.String(50), nullable=True, default='') # Asumimos que puede ser opcional

    fecha = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=False)
    motivo = db.Column(db.String(255), nullable=True)
    doctor = db.Column(db.String(100), nullable=False)
    observaciones = db.Column(db.Text, nullable=True)
    estado = db.Column(db.String(20), default='pendiente', nullable=False)

    # --- CAMPOS PARA SOFT DELETE (mantener) ---
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    # --- FIN CAMPOS SOFT DELETE ---

    paciente = db.relationship('Paciente', backref=db.backref('citas', lazy='dynamic'))

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    nombre_completo = db.Column(db.String(150), nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    pacientes = db.relationship('Paciente', back_populates='odontologo', lazy='dynamic', cascade="all, delete-orphan")
    
    # El resto de tus métodos están perfectos
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Usuario {self.username}>'


class AuditLog(db.Model):
    __tablename__ = 'audit_log' # Buena práctica
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True) 
    user_username = db.Column(db.String(150), nullable=True) 
    action_type = db.Column(db.String(50), nullable=False) 
    description = db.Column(db.Text, nullable=False) 
    target_model = db.Column(db.String(50), nullable=True) 
    target_id = db.Column(db.Integer, nullable=True) 
    usuario = db.relationship('Usuario', backref=db.backref('audit_logs', lazy='dynamic'))

    def __repr__(self):
        return f'<AuditLog {self.id} - {self.action_type} por {self.user_username or "Sistema"} en {self.timestamp}>'