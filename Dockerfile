# Usa una imagen oficial de Python como base
FROM python:3.13-slim

# Evita preguntas interactivas
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Crear usuario no-root
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Directorio de trabajo
WORKDIR /code

# Instala dependencias del sistema
RUN apt-get update \
    && apt-get install -y gcc libpq-dev netcat-openbsd curl \
    && apt-get clean

# Copia el requirements
COPY requirements.txt /code/

# Instala las dependencias de Python
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copia el resto del código
COPY . /code/

# Crear directorios con permisos correctos
RUN mkdir -p /code/staticfiles /code/media \
    && chown -R appuser:appuser /code

# Entrypoint
COPY ./entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && \
    chmod +x /entrypoint.sh && \
    chown appuser:appuser /entrypoint.sh

USER appuser

ENTRYPOINT ["/entrypoint.sh"]
