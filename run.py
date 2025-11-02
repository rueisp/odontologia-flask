# app.py (o run.py, en la raíz de tu proyecto)

import os
from dotenv import load_dotenv # Importa load_dotenv
from clinica import create_app
# from manage import cli # Solo si realmente lo necesitas para CLI en dev.
                       # En producción, esto no se ejecutará con Gunicorn.

# --- Cargar variables de entorno para desarrollo local ---
# Esto DEBE ejecutarse antes de que create_app() lea os.environ.get()
load_dotenv() 

app = create_app()

# --- Añadir comandos CLI (solo si manage.py es tu fuente de comandos Flask-CLI) ---
# Esto es para uso local con 'flask <comando>', no para el servidor web en producción.
# if 'cli' in locals(): # Verifica si 'cli' fue importado
#    app.cli.add_command(cli)
# else:
#    # Si manage.py no existe o no tiene 'cli', puedes añadir los comandos de Flask-Migrate directamente
#    from flask_migrate import MigrateCommand
#    app.cli.add_command('db', MigrateCommand) # Si quieres comandos 'flask db ...' en local

# --- Iniciar la aplicación en modo de desarrollo (cuando se ejecuta 'python app.py') ---
if __name__ == '__main__':
    # Usar la variable de entorno FLASK_DEBUG para controlar el modo debug
    # Por defecto, si FLASK_DEBUG no está configurado o es '0', será False.
    # Para activarlo: export FLASK_DEBUG=1 (Linux/macOS) o set FLASK_DEBUG=1 (Windows) antes de ejecutar.
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', host='0.0.0.0', port=5000)