import json
from functools import wraps

from flask import Blueprint, g, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, jwt
from app.cache import redis_client
from app.models import User


auth_bp = Blueprint('auth', __name__)

AUTH_CACHE_TTL = 60


def _cache_key(user_id: int) -> str:
    return f"auth:user:{user_id}"


def _load_user_from_identity(identity: str):
    """Carga el usuario autenticado con un cache muy corto en Redis."""
    user_id = int(identity)
    cache_key = _cache_key(user_id)
    cached = redis_client.get(cache_key)
    if cached is not None:
        try:
            payload = json.loads(cached)
            return payload
        except Exception:
            pass

    user = User.query.get(user_id)
    if user is None:
        return None

    payload = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
    }
    redis_client.setex(cache_key, AUTH_CACHE_TTL, json.dumps(payload))
    return payload


def auth_required(fn):
    """Decorador reutilizable para proteger rutas con JWT y cachear el usuario."""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        identity = get_jwt_identity()
        user = _load_user_from_identity(identity)
        if user is None:
            return jsonify({'error': 'Usuario no encontrado'}), 401
        g.current_user = user
        return fn(*args, **kwargs)
    return wrapper


@auth_bp.route('/register', methods=['POST'])
def register():
    payload = request.get_json(silent=True) or {}
    username = payload.get('username')
    email = payload.get('email')
    password = payload.get('password')

    if not username or not email or not password:
        return jsonify({'error': 'username, email y password son obligatorios'}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({'error': 'Usuario o email ya existe'}), 409

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({
        'message': 'Usuario registrado correctamente',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
        },
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    payload = request.get_json(silent=True) or {}
    username_or_email = payload.get('username') or payload.get('email')
    password = payload.get('password')

    if not username_or_email or not password:
        return jsonify({'error': 'username/email y password son obligatorios'}), 400

    user = User.query.filter(
        (User.username == username_or_email) | (User.email == username_or_email)
    ).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Credenciales inválidas'}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({
        'message': 'Login correcto',
        'access_token': token,
        'token_type': 'bearer',
    }), 200
