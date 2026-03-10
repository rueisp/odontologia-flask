\# 📘 Guía de Comandos - Sistema Odontológico



\## 📦 \*\*GITHUB (Control de versiones)\*\*



```bash

\# 1. Ver cambios

git status



\# 2. Agregar archivos modificados

git add .



\# 3. Hacer commit

git commit -m "Descripción clara del cambio"



\# 4. Subir a GitHub

git push origin version-simple

```



\## 🚀 \*\*GOOGLE CLOUD RUN (Despliegue)\*\*



```bash

\# 5. Construir imagen (INCREMENTA VERSIÓN: v1, v2, v3...)

gcloud builds submit --tag gcr.io/odontologia-app-rps/odontologia-flask:v6



\# 6. Desplegar en Cloud Run

gcloud run deploy clinica-test --image gcr.io/odontologia-app-rps/odontologia-flask:v6 --region us-central1 --allow-unauthenticated

```



\## 🔍 \*\*COMANDOS ÚTILES\*\*



\### Ver logs de errores

```bash

gcloud logging read "resource.type=cloud\_run\_revision AND resource.labels.service\_name=clinica-test AND severity>=ERROR" --limit 10

```



\### Ver variables de entorno

```bash

gcloud run services describe clinica-test --region us-central1 --format="yaml(spec.template.spec.containers.env)"

```



\### Ver URL del servicio

```bash

gcloud run services describe clinica-test --region us-central1 --format="value(status.url)"

```



\## ⚠️ \*\*RECORDATORIOS IMPORTANTES\*\*

\- ✅ \*\*Siempre incrementa el número de versión\*\* (v1 → v2 → v3...)

\- ✅ \*\*Haz `git status` antes de commit\*\* para no olvidar archivos

\- ✅ \*\*Espera a que termine cada comando\*\* antes de ejecutar el siguiente

\- ✅ \*\*Prueba la URL después de desplegar\*\*

