import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base configuration with default settings."""
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key-for-development-only")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "₹")

    # MySQL connection parameters
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "ai_budget_db")

    # MySQL connection string using PyMySQL driver
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    )

    # Engine options for MySQL connection pooling and timeout handling
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 280,
        "pool_pre_ping": True,
    }


class DevelopmentConfig(Config):
    """Configuration for local development."""
    DEBUG = True
    FLASK_ENV = "development"


class TestingConfig(Config):
    """Configuration for automated test suite (Pytest)."""
    TESTING = True
    DEBUG = False
    # Use fast in-memory SQLite for isolated automated unit tests
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_ENGINE_OPTIONS = {}


class ProductionConfig(Config):
    """Configuration for live production deployment."""
    DEBUG = False
    FLASK_ENV = "production"


# Mapping dictionary to select configuration class by environment name
config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
