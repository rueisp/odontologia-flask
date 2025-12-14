# Dockerfile (en la raíz del proyecto, junto a 'requirements.txt')

FROM python:3.11.4-slim
WORKDIR /usr/src/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "clinica:app"]