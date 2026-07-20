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

## 5) Comparación antes/después

### A. Mostrar el efecto de N+1 en GET /rooms/list

1. Activa el log de SQLAlchemy temporalmente en el arranque de la app:\n   - En la app Flask, puedes fijar `app.config['SQLALCHEMY_ECHO'] = True` justo antes de `db.init_app(app)` o al iniciar la app desde un script de prueba.\n   - También puedes contar las consultas de base de datos observando el log de la consola mientras haces la petición.
2. Ejecuta dos peticiones desde Postman/Insomnia:
   - `GET /rooms/list?optimized=false`
   - `GET /rooms/list?optimized=true`
3. Compara el resultado en la consola de Flask: el modo `optimized=false` debe mostrar más consultas por el patrón N+1, mientras que `optimized=true` debe reducirlas gracias a `joinedload(Room.host)`.
4. En Postman, abre la pestaña de tiempo de respuesta y registra los valores de ambos endpoints en la tabla de abajo.

| Endpoint | Nº de queries | Tiempo de respuesta |
| --- | ---: | ---: |
| GET /rooms/list?optimized=false | ___ | ___ |
| GET /rooms/list?optimized=true | ___ | ___ |

### B. Mostrar la diferencia entre cache miss y cache hit en GET /rooms/<id>

1. Haz una primera petición a `GET /rooms/<id>` para provocar un cache miss. El body debe devolver `"source": "db"` y se debe guardar la clave en Redis.
2. Haz una segunda petición inmediata al mismo endpoint para provocar un cache hit. El body debe devolver `"source": "cache"`.
3. En Postman/Insomnia, compara el tiempo de respuesta de la primera y la segunda llamada. La segunda debería ser más rápida.

| Endpoint | Resultado | Tiempo de respuesta |
| --- | --- | ---: |
| GET /rooms/<id> (primera vez) | source = "db" | ___ |
| GET /rooms/<id> (segunda vez) | source = "cache" | ___ |
