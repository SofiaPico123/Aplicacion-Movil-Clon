import json
from flask import Blueprint, jsonify, request
from sqlalchemy.orm import joinedload

from app import db
from app.auth.routes import auth_required
from app.cache import redis_client
from app.models import Room, User
from app.tasks import process_audio_session

# Endpoint POST /rooms/<room_id>/process-audio:
# Ejecuta la tarea pesada en segundo plano (Celery) y retorna 202 con el task_id.

rooms_bp = Blueprint('rooms', __name__)

CACHE_TTL = 300  # Tiempo de vida de la caché: 5 minutos (300 segundos)


def _cache_key(room_id: str) -> str:
    return f"rooms:{room_id}"


def _room_to_payload(room: Room) -> dict:
    return {
        'id': room.id,
        'name': room.name,
        'active': room.active,
        'host_id': room.host_id,
        'host': {
            'id': room.host.id,
            'username': room.host.username,
            'email': room.host.email,
        } if room.host else None,
    }


# ===== Estrategia Cache-Aside e Invalidación =====

# GET lista de salas
# Para demostrar el problema N+1, la ruta acepta ?optimized=true/false.
# Con optimized=false se accede a room.host.username por cada room,
# provocando consultas adicionales por cada elemento. Con optimized=true
# pensamos en one-join usando joinedload(Room.host), que evita ese patrón.
@rooms_bp.route('/rooms/list', methods=['GET'])
def list_rooms():
    try:
        optimized = request.args.get('optimized', 'false').lower() in {'1', 'true', 'yes', 'on'}
        if optimized:
            rooms = Room.query.options(joinedload(Room.host)).filter_by(active=True).all()
        else:
            rooms = Room.query.filter_by(active=True).all()
            # Intencionalmente se accede a room.host.username en cada iteración.
            # Esto reproduce el patrón N+1 con lazy loading del atributo `host`.
            for room in rooms:
                _ = room.host.username

        payload = [_room_to_payload(room) for room in rooms]
        return jsonify({'source': 'db', 'optimized': optimized, 'rooms': payload}), 200
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
    room = Room.query.get(room_id)
    if room is None:
        return jsonify({'error': 'Room not found'}), 404

    # 3. Guardar en Redis usando JSON y TTL (setex)
    redis_client.setex(key, CACHE_TTL, json.dumps(_room_to_payload(room)))

    return jsonify({'source': 'db', 'room': _room_to_payload(room)}), 200


@rooms_bp.route('/rooms/<room_id>/process-audio', methods=['POST'])
@auth_required
def process_audio(room_id: str):
    # Ejecuta la tarea en segundo plano y protege la ruta con JWT.
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
    room = Room.query.get(room_id)

    if room is None:
        # Si no existe, se crea un registro nuevo con datos básicos.
        room = Room(
            id=room_id,
            name=payload.get('name', 'Sala sin nombre'),
            active=payload.get('active', True),
            host_id=payload.get('host_id', 1),
        )
        db.session.add(room)
    else:
        if 'name' in payload:
            room.name = payload['name']
        if 'active' in payload:
            room.active = bool(payload['active'])
        if 'host_id' in payload:
            room.host_id = payload['host_id']

    db.session.commit()

    # Invalidación de caché: eliminar la clave obsoleta de Redis
    redis_client.delete(_cache_key(room_id))
    print(f"--> [CACHE INVALIDATED] Clave eliminada de Redis tras actualización")

    return jsonify({'updated': True, 'room': _room_to_payload(room)}), 200


@rooms_bp.route('/rooms/<room_id>', methods=['DELETE'])
def delete_room(room_id: str):
    room = Room.query.get(room_id)
    if room is None:
        return jsonify({'error': 'Room not found'}), 404

    db.session.delete(room)
    db.session.commit()

    # Invalidación de caché: eliminar clave de Redis
    redis_client.delete(_cache_key(room_id))
    print(f"--> [CACHE INVALIDATED] Clave eliminada de Redis tras eliminación")

    return jsonify({'deleted': True, 'room': _room_to_payload(room)}), 200