# app/__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()

login_manager.login_view = "main.login"

def create_app(config_class=None):
    """Flask app factory"""
    app = Flask(__name__, instance_relative_config=True, template_folder='../templates', static_folder='../static')

    # Load explicit config first (used by tests), otherwise choose by environment.
    if config_class is not None:
        app.config.from_object(config_class)
    else:
        if os.environ.get("DATABASE_URL") or os.environ.get("FLASK_ENV") == "production":
            from config import ProductionConfig
            app.config.from_object(ProductionConfig)
        else:
            from config import DevelopmentConfig
            app.config.from_object(DevelopmentConfig)

    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app
