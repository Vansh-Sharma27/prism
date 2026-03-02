"""
PRISM Backend Application Factory
"""
import os
import secrets
from datetime import timedelta
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


def create_app(config_name=None):
    """Application factory pattern."""
    app = Flask(__name__)

    # Load configuration
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        secret_key = secrets.token_urlsafe(48)
        app.logger.warning(
            "SECRET_KEY not set; generated ephemeral key for this process. "
            "Set SECRET_KEY in environment for stable production security."
        )

    jwt_secret = os.getenv('JWT_SECRET_KEY')
    if not jwt_secret:
        jwt_secret = secrets.token_urlsafe(48)
        app.logger.warning(
            "JWT_SECRET_KEY not set; generated ephemeral key for this process. "
            "Set JWT_SECRET_KEY in environment for stable token verification."
        )

    app.config['SECRET_KEY'] = secret_key
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL', 
        'sqlite:///prism_dev.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = jwt_secret
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(
        hours=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 24))
    )
    app.config['ALLOW_PUBLIC_READS'] = (
        os.getenv('PRISM_ALLOW_PUBLIC_READS', 'false').lower() == 'true'
    )
    app.config['ALLOW_PRIVILEGED_SELF_REGISTER'] = (
        os.getenv('PRISM_ALLOW_PRIVILEGED_SELF_REGISTER', 'false').lower() == 'true'
    )

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    allowed_origins = [
        origin.strip()
        for origin in os.getenv(
            'CORS_ALLOWED_ORIGINS',
            'http://localhost:3000,http://127.0.0.1:3000'
        ).split(',')
        if origin.strip()
    ]
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

    # Register blueprints
    from app.routes.health import health_bp
    from app.routes.slots import slots_bp
    from app.routes.lots import lots_bp
    from app.routes.auth import auth_bp
    from app import models  # noqa: F401 - ensure model metadata is loaded

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(slots_bp, url_prefix='/api/v1')
    app.register_blueprint(lots_bp, url_prefix='/api/v1')
    
    # Optional bootstrap mode for quick local smoke tests without migrations.
    if os.getenv('PRISM_AUTO_CREATE_TABLES', 'false').lower() == 'true':
        with app.app_context():
            db.create_all()
    
    return app
