#!/bin/sh
# Ejecutar migraciones
echo "Ejecutando migraciones de base de datos..."
flask db upgrade

# Iniciar Gunicorn con configuración optimizada
echo "Iniciando Gunicorn..."
exec gunicorn --bind :8080 \
              --workers 1 \
              --threads 4 \
              --timeout 120 \
              --worker-class gthread \
              --max-requests 1000 \
              --max-requests-jitter 50 \
              --access-logfile - \
              --error-logfile - \
              "run:app"