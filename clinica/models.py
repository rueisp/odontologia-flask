from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from flask_login import UserMixin 
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db
import pytz

class Paciente(db.Model):
    __tablename__ = 'paciente'

    id = db.Column(db.Integer, primary_key=True)
    
    # ============================================================
    # CAMPOS ORIGINALES - NO TOCAR (Mantienen tu interfaz actual)
    # ============================================================
    nombres = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    
    # --- Campos de Nombres Separados para RIPS ---
    primer_nombre = db.Column(db.String(60), nullable=True)
    segundo_nombre = db.Column(db.String(60), nullable=True)
    primer_apellido = db.Column(db.String(60), nullable=True)
    segundo_apellido = db.Column(db.String(60), nullable=True)

    tipo_documento = db.Column(db.String(50), nullable=True)  # ORIGINAL - Se mantiene
    documento = db.Column(db.String(50), unique=True, nullable=True)
    fecha_nacimiento = db.Column(db.Date, nullable=True)
    edad = db.Column(db.Integer, nullable=True)
    email = db.Column(db.String(100), nullable=True)
    telefono = db.Column(db.String(50), nullable=False)
    genero = db.Column(db.String(50), nullable=True)  # ORIGINAL - Se mantiene
    estado_civil = db.Column(db.String(50), nullable=True)
    direccion = db.Column(db.String(200), nullable=True)
    barrio = db.Column(db.String(100), nullable=True)
    municipio = db.Column(db.String(100), nullable=True)
    departamento = db.Column(db.String(100), nullable=True)
    aseguradora = db.Column(db.String(100), nullable=True)  # ORIGINAL - Se mantiene
    tipo_vinculacion = db.Column(db.String(50), nullable=True)  # ORIGINAL - Se mantiene
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
    imagen_perfil_url = db.Column(db.String(255), nullable=True)
    odontologo_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    # ============================================================
    # CAMPOS NUEVOS EXCLUSIVOS PARA RIPS (No afectan la interfaz)
    # ============================================================
    
    # --- Campos de ubicación RIPS ---
    codigo_municipio = db.Column(db.String(5), nullable=True)  # Código DIVIPOLA
    codigo_departamento = db.Column(db.String(2), nullable=True)  # Código DIVIPOLA
    zona_residencia = db.Column(db.String(1), nullable=True, default='U')  # U=Urbano, R=Rural
    pais_residencia = db.Column(db.String(3), nullable=True, default='170')  # 170=Colombia
    
    # --- Campos de aseguramiento RIPS ---
    codigo_aseguradora = db.Column(db.String(6), nullable=True)  # Código oficial de la EPS
    tipo_usuario_rips = db.Column(db.String(2), nullable=True)  # 01=Cotizante, 02=Beneficiario, etc.
    tipo_afiliado = db.Column(db.String(1), nullable=True)
    # --- Campos normalizados para RIPS (se calculan automáticamente) ---
    tipo_documento_rips = db.Column(db.String(2), nullable=True)  # CC, TI, RC, CE, PA
    genero_rips = db.Column(db.String(1), nullable=True)  # M, F
    tipo_vinculacion_rips = db.Column(db.String(1), nullable=True)  # C, S, P, O
    
    # --- RELACIONES ORIGINALES ---
    odontologo = db.relationship('Usuario', back_populates='pacientes')
    evoluciones = db.relationship('Evolucion', backref='paciente', lazy='dynamic')
    
    # ============================================================
    # MÉTODOS HELPER PARA CONVERTIR A FORMATO RIPS
    # ============================================================
    
    def get_tipo_documento_rips(self):
        """Convierte el tipo de documento a formato RIPS (2 caracteres)"""
        if not self.tipo_documento:
            return None
        
        mapeo = {
            'CC': 'CC', 'CEDULA': 'CC', 'CÉDULA': 'CC', 'CEDULA DE CIUDADANIA': 'CC',
            'TI': 'TI', 'TARJETA DE IDENTIDAD': 'TI',
            'RC': 'RC', 'REGISTRO CIVIL': 'RC',
            'CE': 'CE', 'CEDULA DE EXTRANJERIA': 'CE',
            'PA': 'PA', 'PASAPORTE': 'PA',
            'MS': 'MS', 'MENOR SIN IDENTIFICACION': 'MS',
            'AS': 'AS', 'ADULTO SIN IDENTIFICACION': 'AS'
        }
        
        tipo_upper = self.tipo_documento.upper().strip()
        return mapeo.get(tipo_upper, 'CC')  # Por defecto CC
    
    def get_genero_rips(self):
        """Convierte el género a formato RIPS (1 carácter)"""
        if not self.genero:
            return None
        
        genero_upper = self.genero.upper().strip()
        if genero_upper in ['M', 'MASCULINO', 'HOMBRE', 'MALE']:
            return 'M'
        elif genero_upper in ['F', 'FEMENINO', 'MUJER', 'FEMALE']:
            return 'F'
        return 'M'  # Por defecto
    
    def get_tipo_vinculacion_rips(self):
        """Convierte el tipo de vinculación a formato RIPS (1 carácter)"""
        if not self.tipo_vinculacion:
            return 'P'  # Por defecto Particular
        
        mapeo = {
            'CONTRIBUTIVO': 'C', 'C': 'C',
            'SUBSIDIADO': 'S', 'S': 'S',
            'PARTICULAR': 'P', 'P': 'P', 'PREPAGADA': 'P',
            'OTRO': 'O', 'O': 'O', 'VINCULADO': 'O'
        }
        
        tipo_upper = self.tipo_vinculacion.upper().strip()
        return mapeo.get(tipo_upper, 'P')
    
    def actualizar_campos_rips(self):
        """
        Actualiza automáticamente los campos RIPS calculados.
        Llamar este método antes de guardar el paciente.
        """
        self.tipo_documento_rips = self.get_tipo_documento_rips()
        self.genero_rips = self.get_genero_rips()
        self.tipo_vinculacion_rips = self.get_tipo_vinculacion_rips()


class Evolucion(db.Model):
    __tablename__ = 'evolucion'

    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=False)        


class Cita(db.Model):
    __tablename__ = 'cita'

    id = db.Column(db.Integer, primary_key=True)
    
    # ============================================================
    # CAMPOS ORIGINALES - NO TOCAR
    # ============================================================
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=True) 
    paciente_nombres_str = db.Column(db.String(100), nullable=False, default='Paciente sin registrar') 
    paciente_apellidos_str = db.Column(db.String(100), nullable=False, default='') 
    paciente_telefono_str = db.Column(db.String(50), nullable=True, default='')
    fecha = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=False)
    motivo = db.Column(db.String(255), nullable=True)
    doctor = db.Column(db.String(100), nullable=False)
    observaciones = db.Column(db.Text, nullable=True)
    estado = db.Column(db.String(20), default='pendiente', nullable=False)
    factura_id = db.Column(db.Integer, db.ForeignKey('facturas.id'), nullable=True)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    # ============================================================
    # CAMPOS NUEVOS EXCLUSIVOS PARA RIPS (Archivo AC - Consultas)
    # ============================================================
    
    # Estos campos se llenan SOLO cuando se vaya a generar RIPS
    finalidad_consulta = db.Column(db.String(2), nullable=True)  # 10, 20, 30, etc.
    causa_externa = db.Column(db.String(2), nullable=True, default='15')  # 15=Ninguna
    diagnostico_principal = db.Column(db.String(4), nullable=True)  # CIE-10
    diagnostico_relacionado1 = db.Column(db.String(4), nullable=True)
    diagnostico_relacionado2 = db.Column(db.String(4), nullable=True)
    diagnostico_relacionado3 = db.Column(db.String(4), nullable=True)
    tipo_diagnostico_principal = db.Column(db.String(1), nullable=True, default='1')
    
    # --- Campo para Código de Consulta (RIPS) ---
    codigo_consulta_cups = db.Column(db.String(20), nullable=True) # Ej: 890201
    
    # --- RELACIONES ORIGINALES ---
    paciente = db.relationship('Paciente', backref=db.backref('citas', lazy='dynamic'))


# ============================================================
# TABLAS DE CÓDIGOS (NUEVAS - No afectan nada existente)
# ============================================================

class CIE10(db.Model):
    """Tabla de códigos de diagnósticos CIE-10"""
    __tablename__ = 'cie10_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(4), unique=True, nullable=False)  # Ej: K02, K04
    descripcion = db.Column(db.String(255), nullable=False)
    categoria = db.Column(db.String(100), nullable=True)  # Ej: "Enfermedades bucales"
    
    def __repr__(self):
        return f"<CIE10 {self.codigo}: {self.descripcion}>"


class Municipio(db.Model):
    """Tabla de municipios con códigos DIVIPOLA"""
    __tablename__ = 'municipios'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(5), unique=True, nullable=False)  # Código DIVIPOLA
    nombre = db.Column(db.String(100), nullable=False)
    codigo_departamento = db.Column(db.String(2), nullable=False)
    nombre_departamento = db.Column(db.String(100), nullable=False)
    
    def __repr__(self):
        return f"<Municipio {self.codigo}: {self.nombre}>"

    def to_dict(self):
        """Convierte el objeto Municipio a un diccionario para usarlo con JSON."""
        return {
            'codigo': self.codigo,
            'nombre': self.nombre,
            'codigo_departamento': self.codigo_departamento
        }

class EPS(db.Model):
    """Tabla de EPS/Aseguradoras con códigos oficiales"""
    __tablename__ = 'eps'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(6), unique=True, nullable=False)  # Código oficial
    nombre = db.Column(db.String(150), nullable=False)
    activa = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f"<EPS {self.codigo}: {self.nombre}>"
    

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    nombre_completo = db.Column(db.String(150), nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    pacientes = db.relationship('Paciente', back_populates='odontologo', lazy='dynamic', cascade="all, delete-orphan")
    
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
    

class Factura(db.Model):
    __tablename__ = 'facturas'

    id = db.Column(db.Integer, primary_key=True)
    # --- Datos para RIPS Archivo de Transacciones (AF) ---
    numero_factura = db.Column(db.String(20), unique=True, nullable=False)
    fecha_factura = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(pytz.utc))
    valor_total = db.Column(db.Float, nullable=False, default=0.0)
    
    # --- Campos de Valor Detallados para RIPS ---
    valor_copago = db.Column(db.Float, nullable=True, default=0.0)
    valor_cuota_moderadora = db.Column(db.Float, nullable=True, default=0.0)
    valor_comision = db.Column(db.Float, nullable=True, default=0.0)
    valor_descuentos = db.Column(db.Float, nullable=True, default=0.0)
    
    # Fechas del periodo de facturación (Opcionales, pero útiles para RIPS)
    fecha_inicio_periodo = db.Column(db.Date, nullable=True)
    fecha_final_periodo = db.Column(db.Date, nullable=True)

    # --- Relaciones (La clave para conectar todo) ---
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=False)
    paciente = db.relationship('Paciente', backref=db.backref('facturas', lazy=True))

    # Esta relación es importante: una factura puede tener muchas citas/procedimientos.
    citas = db.relationship('Cita', backref='factura', lazy='dynamic')

    def __repr__(self):
        return f"<Factura No: {self.numero_factura}>"
    

class Procedimiento(db.Model):
    __tablename__ = 'procedimientos'

    id = db.Column(db.Integer, primary_key=True)
    
    # --- Relación con la Cita ---
    # Cada procedimiento pertenece a UNA cita.
    cita_id = db.Column(db.Integer, db.ForeignKey('cita.id'), nullable=False)
    cita = db.relationship('Cita', backref=db.backref('procedimientos', lazy='dynamic', cascade="all, delete-orphan"))

    # --- DATOS CRUCIALES PARA RIPS (Archivo AP) ---
    codigo_cups = db.Column(db.String(20), nullable=False)
    diagnostico_cie10 = db.Column(db.String(20), nullable=False)
    
    # --- Datos adicionales (muy útiles) ---
    descripcion = db.Column(db.String(255), nullable=True) # Ej: "Resina compuesta en pieza 24"
    valor = db.Column(db.Float, nullable=False, default=0.0)

    def __repr__(self):
        return f"<Procedimiento CUPS: {self.codigo_cups} en Cita ID: {self.cita_id}>"


class CUPSCode(db.Model):
    __tablename__ = 'cups_codes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False) # Para el código CUPS
    description = db.Column(db.String(255), nullable=False) # Para el nombre del procedimiento

    def __repr__(self):
        return f"<CUPSCode {self.code}: {self.description}>"