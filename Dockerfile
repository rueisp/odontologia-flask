FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Instalar Python 3.10, pip y wkhtmltopdf
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    wkhtmltopdf \
    xvfb \
    libxrender1 \
    libxext6 \
    libx11-6 \
    libfontconfig1 \
    libfreetype6 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.10 /usr/bin/python \
    && ln -sf /usr/bin/pip3 /usr/bin/pip

WORKDIR /app

# Copiamos primero los requerimientos para instalar librerías
COPY requirements.txt .

# Instalamos las librerías necesarias
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto de tu código al servidor
COPY . .

# --- NUEVA LÍNEA: Le dice a Flask que tu archivo principal es run.py ---
ENV FLASK_APP=run.py

# Copiar entrypoint.sh y dar permisos de ejecución
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Informamos que el contenedor usará el puerto 8080
EXPOSE 8080

# Usar entrypoint.sh en lugar de CMD directo
ENTRYPOINT ["/entrypoint.sh"]