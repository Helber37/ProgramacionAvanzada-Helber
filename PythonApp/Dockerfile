FROM python:3.14.7-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia los requisitos si tienes un requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de los archivos
COPY . .

#Expone el puesto
EXPOSE 5216
# Comando por defecto (se puede sobrescribir en docker-compose.yml)
CMD ["python", "main.py"]