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
    
    tipo_documento = db.Column(db.String(50), nullable=True)  # ORIGINAL - Se mantiene
    documento = db.Column(db.String(50), unique=True, nullable=True)
    fecha_nacimiento = db.Column(db.Date, nullable=True)
    edad = db.Column(db.Integer, nullable=True)
    sexo = db.Column(db.String(1), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    telefono = db.Column(db.String(50), nullable=False)
    direccion = db.Column(db.String(200), nullable=True)
    barrio = db.Column(db.String(100), nullable=True)
    motivo_consulta = db.Column(db.Text, nullable=True)
    enfermedad_actual = db.Column(db.Text, nullable=True)
    alergias = db.Column(db.Text, nullable=True)
    observaciones = db.Column(db.Text, nullable=True)
    dentigrama_canvas = db.Column(db.String(255), nullable=True)
    imagen_perfil_url = db.Column(db.String(255), nullable=True)
    odontologo_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    # --- RELACIONES ORIGINALES ---
    odontologo = db.relationship('Usuario', back_populates='pacientes')
    evoluciones = db.relationship('Evolucion', backref='paciente', lazy='dynamic')
    


class Evolucion(db.Model):
    __tablename__ = 'evolucion'

    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=False)        


class Cita(db.Model):
    __tablename__ = 'cita'
    __table_args__ = (
        db.Index('idx_cita_fecha_odontologo', 'fecha', 'odontologo_id'),
        db.Index('idx_cita_estado', 'estado'),
    )

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=True)
    fecha = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=False)
    motivo = db.Column(db.String(255), nullable=True)
    doctor = db.Column(db.String(100), nullable=False)
    odontologo_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    observaciones = db.Column(db.Text, nullable=True)
    estado = db.Column(db.String(20), default='pendiente', nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    # Campos para pre-registro (solo si paciente_id es NULL)
    pre_nombres = db.Column(db.String(100), nullable=True)
    pre_apellidos = db.Column(db.String(100), nullable=True)
    pre_telefono = db.Column(db.String(50), nullable=True)
    
    # Relaciones
    paciente = db.relationship('Paciente', backref='citas', foreign_keys=[paciente_id])
    odontologo = db.relationship('Usuario', backref='citas', foreign_keys=[odontologo_id])

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    nombre_completo = db.Column(db.String(150), nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    pacientes = db.relationship('Paciente', back_populates='odontologo', lazy='dynamic', cascade="all, delete-orphan")
    
    # ↓↓↓ AQUÍ AGREGAR LAS NUEVAS RELACIONES ↓↓↓
    # AGREGAR ESTAS 3 LÍNEAS:
    planes = db.relationship('UsuarioPlan', back_populates='usuario', cascade='all, delete-orphan')
    limites_diarios = db.relationship('LimiteDiario', back_populates='usuario', cascade='all, delete-orphan')
    auditoria_accesos = db.relationship('AuditoriaAcceso', back_populates='usuario', cascade='all, delete-orphan')
    # ↑↑↑ FIN DE LAS NUEVAS RELACIONES ↑↑↑
    

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
    


# ============================================================
# NUEVAS TABLAS PARA SISTEMA DE PLANES Y SEGURIDAD
# ============================================================

class Plan(db.Model):
    """Tabla de planes disponibles (trial, básico, profesional)"""
    __tablename__ = 'planes'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)  # trial, basico, profesional
    descripcion = db.Column(db.String(200), nullable=True)
    precio_mensual = db.Column(db.Float, nullable=False, default=0.0)  # 0 para trial
    limite_pacientes_diario = db.Column(db.Integer, nullable=False, default=10)
    precio_cop = db.Column(db.Integer, nullable=False, default=0) # <-- Precio fijo en Pesos Colombianos
    limite_pacientes_diario_primeros_7_dias = db.Column(db.Integer, nullable=False, default=20)
    duracion_trial_dias = db.Column(db.Integer, nullable=False, default=7)  # Solo para trial
    caracteristicas = db.Column(db.JSON, nullable=True)  # Lista de características en JSON
    activo = db.Column(db.Boolean, default=True, nullable=False)
    orden = db.Column(db.Integer, default=0, nullable=False)  # Para ordenar en la UI
    
    
    # Relaciones
    usuarios_planes = db.relationship('UsuarioPlan', back_populates='plan', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Plan {self.nombre}: ${self.precio_mensual}/mes>'

class UsuarioPlan(db.Model):
    """Relación entre usuario y plan (historial de suscripciones)"""
    __tablename__ = 'usuarios_planes'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('planes.id'), nullable=False)
    
    # Estado de la suscripción
    estado = db.Column(db.String(20), nullable=False, default='activo')  # activo, cancelado, expirado, trial
    fecha_inicio = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_fin = db.Column(db.DateTime, nullable=True)  # Null = renovación automática
    fecha_cancelacion = db.Column(db.DateTime, nullable=True)
    es_trial = db.Column(db.Boolean, default=False, nullable=False)
    
    # Límites especiales para trial
    trial_dias_restantes = db.Column(db.Integer, nullable=True)
    trial_pacientes_primeros_7_dias = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relaciones
    usuario = db.relationship('Usuario', back_populates='planes')
    plan = db.relationship('Plan', back_populates='usuarios_planes')
    pagos = db.relationship('Pago', back_populates='usuario_plan', cascade='all, delete-orphan')
    
    # Índices para búsquedas frecuentes
    __table_args__ = (
        db.Index('idx_usuario_plan_activo', 'usuario_id', 'estado'),
        db.Index('idx_usuario_fecha_fin', 'usuario_id', 'fecha_fin'),
    )
    
    def __repr__(self):
        return f'<UsuarioPlan usuario:{self.usuario_id} plan:{self.plan_id} estado:{self.estado}>'


class LimiteDiario(db.Model):
    """Contador diario de pacientes por usuario"""
    __tablename__ = 'limites_diarios'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    contador_pacientes = db.Column(db.Integer, nullable=False, default=0)
    limite_actual = db.Column(db.Integer, nullable=False, default=10)
    
    # Para tracking de trial
    es_dia_trial = db.Column(db.Boolean, default=False, nullable=False)
    dia_numero_trial = db.Column(db.Integer, nullable=True)
    
    # Relación
    usuario = db.relationship('Usuario', back_populates='limites_diarios')
    
    # Índice único para evitar duplicados por usuario/fecha
    __table_args__ = (
        db.UniqueConstraint('usuario_id', 'fecha', name='uq_usuario_fecha'),
    )
    
    def __repr__(self):
        return f'<LimiteDiario usuario:{self.usuario_id} fecha:{self.fecha} {self.contador_pacientes}/{self.limite_actual}>'


class Pago(db.Model):
    """Historial de pagos de suscripciones"""
    __tablename__ = 'pagos'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_plan_id = db.Column(db.Integer, db.ForeignKey('usuarios_planes.id'), nullable=False)
    
    # Información del pago
    monto = db.Column(db.Float, nullable=False)
    moneda = db.Column(db.String(3), nullable=False, default='USD')
    metodo_pago = db.Column(db.String(50), nullable=True)  # stripe, paypal, etc.
    id_transaccion = db.Column(db.String(100), nullable=True, unique=True)  # ID de la transacción externa
    estado = db.Column(db.String(20), nullable=False, default='completado')  # completado, fallido, pendiente, reembolsado
    
    # Fechas
    fecha_pago = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_vencimiento = db.Column(db.DateTime, nullable=True)
    periodo_inicio = db.Column(db.DateTime, nullable=False)
    periodo_fin = db.Column(db.DateTime, nullable=False)
    
    # Metadatos
    metadatos = db.Column(db.JSON, nullable=True)  # Datos adicionales del pago
    
    # Relación
    usuario_plan = db.relationship('UsuarioPlan', back_populates='pagos')
    
    def __repr__(self):
        return f'<Pago ${self.monto} {self.moneda} - {self.estado}>'



class SolicitudPago(db.Model):
    __tablename__ = 'solicitudes_pago_manual'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('planes.id'), nullable=False)
    plan_nombre = db.Column(db.String(80), nullable=False)
    monto_cop = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.String(20), default='PENDIENTE', nullable=False)
    fecha_solicitud = db.Column(db.DateTime, default=db.func.now())
    fecha_verificacion = db.Column(db.DateTime, nullable=True)
    comprobante_url = db.Column(db.String(255), nullable=True)

    usuario = db.relationship('Usuario', backref='solicitudes_pago')

    def __repr__(self):
        return f"<SolicitudPago {self.id} - {self.plan_nombre} - {self.estado}>"


class AuditoriaAcceso(db.Model):
    """Tracking de accesos y acciones importantes"""
    __tablename__ = 'auditoria_accesos'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    usuario_email = db.Column(db.String(120), nullable=True)  # Backup por si se elimina usuario
    
    # Información de la acción
    tipo_accion = db.Column(db.String(50), nullable=False)  # login, logout, crear_paciente, exceder_limite
    descripcion = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    
    # Recurso afectado
    recurso_tipo = db.Column(db.String(50), nullable=True)  # paciente, cita, factura
    recurso_id = db.Column(db.Integer, nullable=True)
    
    # Fecha
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Metadatos adicional
    metadatos = db.Column(db.JSON, nullable=True)
    
    # Relación
    usuario = db.relationship('Usuario', back_populates='auditoria_accesos')
    
    def __repr__(self):
        return f'<AuditoriaAcceso {self.tipo_accion} - {self.usuario_email or "Sistema"}>'    
    

class PagoPaciente(db.Model):
    __tablename__ = 'pagos_paciente'

    id = db.Column(db.Integer, primary_key=True)  # Cambiado de UUID a Integer
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    descripcion = db.Column(db.Text, nullable=False, default='')
    monto = db.Column(db.Integer, nullable=False, default=0)
    metodo_pago = db.Column(db.Text, nullable=True)
    observacion = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relación con Paciente (opcional pero útil)
    paciente = db.relationship('Paciente', backref=db.backref('pagos_paciente', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<PagoPaciente {self.fecha} - ${self.monto}>'   

# models.py - AGREGAR ESTA NUEVA TABLA (NO eliminar PagoPaciente aún)

class PagoUnificado(db.Model):
    """SISTEMA UNIFICADO DE PAGOS - Nueva tabla central"""
    __tablename__ = 'pagos_unificados'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # ============================================================
    # CAMPOS OBLIGATORIOS SIEMPRE
    # ============================================================
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    hora = db.Column(db.Time, nullable=False, default=datetime.now().time())
    descripcion = db.Column(db.String(255), nullable=False)  # Breve descripción
    monto = db.Column(db.Integer, nullable=False)  # En centavos/pesos
    metodo_pago = db.Column(db.String(50), nullable=False)  # Efectivo, Tarjeta, Transferencia
    
    # ============================================================
    # INFORMACIÓN DEL PACIENTE (Siempre guardamos el nombre)
    # ============================================================
    paciente_nombre = db.Column(db.String(200), nullable=False)  # ¡SIEMPRE!
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=True)  # Opcional
    
    # ============================================================
    # CAMPOS ADICIONALES
    # ============================================================
    pagado_por = db.Column(db.String(150), nullable=True)  # Quién realizó el pago
    observacion = db.Column(db.Text, nullable=True)
    
    # ============================================================
    # CONTROL DEL SISTEMA
    # ============================================================
    codigo = db.Column(db.String(20), unique=True, nullable=False)  # Código único para recibo
    es_rapido = db.Column(db.Boolean, default=False, nullable=False)  # True = desde home, False = desde paciente
    
    # ============================================================
    # AUDITORÍA
    # ============================================================
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)  # Quién registró
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # ============================================================
    # RELACIONES
    # ============================================================
    paciente = db.relationship('Paciente', backref=db.backref('pagos_unificados', lazy='dynamic'))
    usuario = db.relationship('Usuario', backref=db.backref('pagos_registrados', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Pago {self.codigo} - {self.paciente_nombre} - ${self.monto}>'
    
    def generar_codigo(self):
        """Genera un código único para el recibo"""
        import random
        import string
        fecha_str = self.fecha.strftime('%Y%m%d')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"R-{fecha_str}-{random_str}"     
