# app.py (o run.py, en la raíz de tu proyecto)

import os
from dotenv import load_dotenv
from clinica import create_app
from flask_migrate import Migrate # <--- Importa Migrate aquí
from clinica.extensions import db # <--- Importa db aquí

# --- Cargar variables de entorno para desarrollo local ---
load_dotenv() 

app = create_app()

# --- Inicializar Flask-Migrate con la aplicación y la base de datos ---
# Esto registra automáticamente los comandos 'db' con Flask CLI
migrate = Migrate(app, db) # <--- Asegúrate de que 'db' se importa de clinica.extensions

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', host='0.0.0.0', port=5000)