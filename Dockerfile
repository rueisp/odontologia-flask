# Usamos una imagen ligera de Python 3.11
FROM python:3.11-slim

# Establecemos la carpeta de trabajo dentro del servidor
WORKDIR /app

# Copiamos primero los requerimientos para instalar librerías
COPY requirements.txt .

# Instalamos las librerías necesarias
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto de tu código al servidor
COPY . .

# --- NUEVA LÍNEA: Le dice a Flask que tu archivo principal es run.py ---
ENV FLASK_APP=run.py

# Informamos que el contenedor usará el puerto 8080
EXPOSE 8080

# Comando de inicio
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "run:app"]