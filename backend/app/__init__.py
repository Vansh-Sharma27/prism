"""
PRISM Backend Application Factory
"""
import os
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
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL', 
        'sqlite:///prism_dev.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', app.config['SECRET_KEY'])
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(
        hours=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 24))
    )

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app)

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
