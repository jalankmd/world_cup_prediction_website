# config.py
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base config with defaults"""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    """Development-specific config"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or \
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'app.db')}"

class ProductionConfig(Config):
    """Production-specific config"""
    DEBUG = False
    # You can set DATABASE_URL in production env (Postgres recommended)
    database_url = os.environ.get("DATABASE_URL")
    SQLALCHEMY_DATABASE_URI = database_url.replace("postgresql://", "postgresql+psycopg://") if database_url else None
