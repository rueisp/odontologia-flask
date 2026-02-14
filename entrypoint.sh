#!/bin/sh
# Ejecutar migraciones
echo "Ejecutando migraciones de base de datos..."
flask db upgrade

# Iniciar la aplicación
echo "Iniciando Gunicorn..."
exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 run:app