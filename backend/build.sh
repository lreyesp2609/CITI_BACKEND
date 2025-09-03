#!/usr/bin/env bash
# build.sh

set -o errexit  # exit on error

# Instalar dependencias
pip install -r requirements.txt

# Hacer migraciones con más tiempo y debugging
echo "Creando migraciones..."
python manage.py makemigrations --verbosity=2

echo "Aplicando migraciones..."
python manage.py migrate --verbosity=2

# Recopilar archivos estáticos
echo "Recopilando archivos estáticos..."
python manage.py collectstatic --no-input --clear

echo "Build completado exitosamente!"