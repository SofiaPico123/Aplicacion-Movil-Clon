# Backend Flask demo para video

## 1) Levantar Redis

```bash
redis-server
```

## 2) Levantar el worker de Celery

Desde la carpeta backend:

```bash
celery -A app.tasks worker --loglevel=info
```

## 3) Levantar Flask

En PowerShell:

```powershell
cd backend
$env:FLASK_APP = "app"
$env:FLASK_ENV = "development"
python -m flask run
```

## 4) Variables de entorno útiles

En PowerShell:

```powershell
$env:DATABASE_URL = "sqlite:///./app.db"
$env:REDIS_HOST = "localhost"
$env:REDIS_PORT = "6379"
$env:REDIS_DB = "0"
$env:JWT_SECRET_KEY = "dev-secret-key"
```
