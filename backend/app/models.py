from app import db


class User(db.Model):
    """Usuario autenticable para el demo de JWT y relaciones con salas."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)

    rooms = db.relationship('Room', back_populates='host', cascade='all, delete-orphan')


class Room(db.Model):
    """Sala que puede ser consultada via cache-aside y relacionada con su host."""
    __tablename__ = 'rooms'

    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    host_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    host = db.relationship('User', back_populates='rooms')
