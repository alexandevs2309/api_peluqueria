# Usa una imagen oficial de Python como base
FROM python:3.13-slim

# Evita preguntas interactivas
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Directorio de trabajo
WORKDIR /code

# Instala dependencias del sistema
RUN apt-get update \
    && apt-get install -y gcc libpq-dev netcat-openbsd \
    && apt-get clean



# Copia el requirements
COPY requirements.txt /code/

# Instala las dependencias de Python
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copia el resto del código
COPY . /code/

# Entrypoint
COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
