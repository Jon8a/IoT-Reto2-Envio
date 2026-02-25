FROM python:3.11-slim

WORKDIR /app

# Copiar dependencias e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar scripts de subscribers
COPY subscriber_director.py .
COPY subscriber_operario.py .

# Por defecto, ejecutar el subscriber director
# Se puede sobrescribir en docker-compose
CMD ["python", "subscriber_director.py"]
