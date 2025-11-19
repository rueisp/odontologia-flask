@echo off
REM Asegurarse de estar en el directorio correcto del proyecto
REM La ruta de tu proyecto es C:\Users\rueis\Proyectos\flask
cd /d "C:\Users\rueis\Proyectos\flask"

REM Activar el entorno virtual 'env'
call env\Scripts\activate.bat

REM Ejecutar la aplicación Flask
python run.py

REM Opcional: Mantener la ventana abierta después de que la app termine (útil para ver errores)
pause