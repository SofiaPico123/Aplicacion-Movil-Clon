import os

from dotenv import load_dotenv
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

load_dotenv()


db = SQLAlchemy()
jwt = JWTManager()


def create_app():
    """Factory de Flask para levantar la app en desarrollo local o con Postgres."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'sqlite:///./app.db',
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = int(
        os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600)
    )

    db.init_app(app)
    jwt.init_app(app)

    with app.app_context():
        from app.models import Room, User  # noqa: F401
        db.create_all()

        if User.query.count() == 0:
            demo_user = User(
                username='demo',
                email='demo@example.com',
                password_hash=generate_password_hash('secret123'),
            )
            db.session.add(demo_user)
            db.session.flush()

            demo_room = Room(
                id='demo-room',
                name='Sala Demo',
                active=True,
                host_id=demo_user.id,
            )
            db.session.add(demo_room)
            db.session.commit()

    from app.auth.routes import auth_bp
    from app.rooms.routes import rooms_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(rooms_bp)

    return app


app = create_app()
