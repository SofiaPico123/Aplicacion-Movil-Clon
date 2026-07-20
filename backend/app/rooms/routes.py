import json
from flask import Blueprint, request, jsonify
from app.cache import redis_client

from sqlalchemy.orm import joinedload

from app.tasks import process_audio_session

# Endpoint POST /rooms/<room_id>/process-audio:
# Ejecuta la tarea pesada en segundo plano (Celery) y retorna 202 con el task_id.


rooms_bp = Blueprint('rooms', __name__)



CACHE_TTL = 300  # Tiempo de vida de la caché: 5 minutos (300 segundos)

def _cache_key(room_id: str) -> str:
    return f"rooms:{room_id}"

# ===== Placeholder de persistencia (Simulación DB) =====
_IN_MEMORY_DB = {}

def _db_get(room_id: str):
    return _IN_MEMORY_DB.get(room_id)

def _db_put(room_id: str, payload: dict):
    _IN_MEMORY_DB[str(room_id)] = payload
    return _IN_MEMORY_DB[str(room_id)]

def _db_delete(room_id: str):
    return _IN_MEMORY_DB.pop(str(room_id), None)


# ===== Estrategia Cache-Aside e Invalidación =====

# GET lista de salas
# Para la corrección de N+1 usamos eager loading (joinedload) sobre la relación `host`.
# Técnicamente: `joinedload(Room.host)` hace un JOIN explícito en la consulta principal,
# evitando que al iterar sobre rooms se ejecuten consultas adicionales por cada room.

@rooms_bp.route('/rooms/list', methods=['GET'])
def list_rooms():
    try:
        # Placeholder: en cuanto conectes SQLAlchemy/Room real, reemplaza esto por:
        # rooms = Room.query.options(joinedload(Room.host)).filter_by(active=True).all()
        rooms = []  # TODO: integrar Room (SQLAlchemy)

        return jsonify({'source': 'db', 'rooms': rooms}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rooms_bp.route('/rooms/<room_id>', methods=['GET'])
def get_room(room_id: str):

    key = _cache_key(room_id)

    # 1. Intentar leer desde Redis (Cache Hit)
    cached = redis_client.get(key)
    if cached is not None:
        try:
            print(f"--> [CACHE HIT] Datos devueltos desde Redis para sala: {room_id}")
            return jsonify({'source': 'cache', 'room': json.loads(cached)}), 200
        except Exception:
            pass  # Si la estructura JSON falla, cae a la DB

    # 2. Si no está en Redis (Cache Miss), consultar la Base de Datos
    print(f"--> [CACHE MISS] Consultando DB para sala: {room_id}")
    room = _db_get(room_id)
    if room is None:
        return jsonify({'error': 'Room not found'}), 404

    # 3. Guardar en Redis usando JSON y TTL (setex)
    redis_client.setex(key, CACHE_TTL, json.dumps(room))

    return jsonify({'source': 'db', 'room': room}), 200


@rooms_bp.route('/rooms/<room_id>/process-audio', methods=['POST'])
def process_audio(room_id: str):
    # Ejecuta la tarea en segundo plano
    task = process_audio_session.delay(room_id)
    return (
        jsonify({
            'message': 'Audio processing started',
            'task_id': task.id,
        }),
        202,
    )


@rooms_bp.route('/rooms/<room_id>', methods=['PUT'])
def put_room(room_id: str):

    payload = request.get_json(silent=True) or {}
    room = _db_put(room_id, payload)

    # Invalidación de caché: eliminar la clave obsoleta de Redis
    redis_client.delete(_cache_key(room_id))
    print(f"--> [CACHE INVALIDATED] Clave eliminada de Redis tras actualización")

    return jsonify({'updated': True, 'room': room}), 200


@rooms_bp.route('/rooms/<room_id>', methods=['DELETE'])
def delete_room(room_id: str):
    deleted = _db_delete(room_id)
    if deleted is None:
        return jsonify({'error': 'Room not found'}), 404

    # Invalidación de caché: eliminar clave de Redis
    redis_client.delete(_cache_key(room_id))
    print(f"--> [CACHE INVALIDATED] Clave eliminada de Redis tras eliminación")

    return jsonify({'deleted': True, 'room': deleted}), 200