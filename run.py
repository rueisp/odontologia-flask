import os
import webbrowser
import threading
import time
from dotenv import load_dotenv # Importa load_dotenv
from clinica import create_app

# --- Cargar variables de entorno para desarrollo local ---
# Esto DEBE ejecutarse antes de que create_app() lea os.environ.get()
load_dotenv() 

app = create_app()

def open_browser():
    """Abre el navegador por defecto después de una breve espera."""
    time.sleep(1.5)  # Espera a que el servidor arranque
    print(" intentando abrir el navegador...")
    webbrowser.open("http://localhost:5000")

if __name__ == '__main__':
    # Check CLOUDINARY_URL
    if not os.environ.get('CLOUDINARY_URL'):
        print("\n" + "="*80)
        print(" ADVERTENCIA: CLOUDINARY_URL no está configurada en el entorno.")
        print(" La subida de imágenes y dentigramas NO funcionará.")
        print(" Asegúrate de tener el archivo .env con la variable CLOUDINARY_URL correcta.")
        print("="*80 + "\n")
    
    # Iniciar el navegador en un hilo separado (solo si no es el proceso de recarga de Werkzeug)
    # Esto evita que se abra dos veces si debug=True
    if os.environ.get('FLASK_DEBUG') != '1' or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
         threading.Thread(target=open_browser).start()

    # Usar la variable de entorno FLASK_DEBUG para controlar el modo debug
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', host='0.0.0.0', port=5000)