ENV_FOLDER=".venv"
 
if [ ! -d "$ENV_FOLDER" ]; then
    python -m venv $ENV_FOLDER
    . $ENV_FOLDER/bin/activate
    pip install pip wheel setuptools -U
    pip install -r requirements.txt
else
    . $ENV_FOLDER/bin/activate
fi
 
 
 
mkdir -p staticfiles
python manage.py collectstatic --no-input
 
python manage.py migrate
 
celery -A projectile worker --loglevel=info --concurrency=4 --logfile=tmp/celery-worker.log &
 
daphne -b 0.0.0.0 -p 8001 projectile.asgi:application