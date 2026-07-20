from app import db


class User(db.Model):
    """Usuario autenticable para el demo de JWT y relaciones con salas."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Para el demo de la semana 8 esta relación queda en lazy='select':
    # no conviene cargar todas las salas del usuario salvo que se acceda a
    # ellas explícitamente; si el modelo creciera mucho, se podría evaluar
    # un patrón más agresivo como selectin o dynamic.
    rooms = db.relationship(
        'Room',
        back_populates='host',
        cascade='all, delete-orphan',
        lazy='select',
    )


class Room(db.Model):
    """Sala que puede ser consultada via cache-aside y relacionada con su host."""
    __tablename__ = 'rooms'

    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    host_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Esta relación queda en lazy='select' porque la mayoría de los
    # endpoints (por ejemplo, GET /rooms/<id> con cache-aside) no necesitan
    # siempre los datos del host; cuando sí se requiere listar varias salas
    # y sus hosts, la ruta GET /rooms/list?optimized=true usa joinedload()
    # para evitar el N+1 sin convertir el modelo en eager por defecto.
    host = db.relationship('User', back_populates='rooms', lazy='select')
