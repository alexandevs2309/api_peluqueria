#!/bin/bash

echo "▶ Esperando a que la base de datos esté lista..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done

echo "▶ Aplicando migraciones..."
python manage.py migrate --noinput

echo "▶ Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

echo "▶ Iniciando aplicación..."
exec "$@"
