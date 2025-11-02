# ping_supabase.py
import os
import psycopg2
import sys
import datetime

# Obtener la DATABASE_URL de Supabase desde el entorno
DATABASE_URL = os.environ.get('DATABASE_URL_SUPABASE') 

if not DATABASE_URL:
    print(f"[{datetime.datetime.now()}] ERROR: DATABASE_URL_SUPABASE no está configurada. No se puede hacer ping a Supabase.", file=sys.stderr)
    sys.exit(1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT 1") # Una consulta simple para mantener la conexión activa
    cur.close()
    conn.close()
    print(f"[{datetime.datetime.now()}] INFO: Ping exitoso a Supabase.")
except Exception as e:
    print(f"[{datetime.datetime.now()}] ERROR: Falló el ping a Supabase: {e}", file=sys.stderr)
    sys.exit(1)