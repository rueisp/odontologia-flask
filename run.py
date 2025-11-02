# run.py (o app.py, en la raíz de tu proyecto)

import os
from dotenv import load_dotenv # Importa load_dotenv
from clinica import create_app

# --- Cargar variables de entorno para desarrollo local ---
# Esto DEBE ejecutarse antes de que create_app() lea os.environ.get()
load_dotenv() 

app = create_app()

if __name__ == '__main__':
    # Usar la variable de entorno FLASK_DEBUG para controlar el modo debug
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', host='0.0.0.0', port=5000)