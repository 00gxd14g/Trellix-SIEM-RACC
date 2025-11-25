"""
Optimized Configuration with Connection Pooling and Caching

Enhanced configuration for production deployments with:
- Connection pooling
- Redis cache configuration
- Query performance monitoring
- Database optimization settings

Author: Database Optimizer Agent
"""

import os
from utils.db_optimizer import configure_connection_pool


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mcafee-siem-editor-secret-key-2024')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))

    # Database configuration
    DATABASE_DIR = os.path.join(os.path.dirname(__file__), 'database')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(DATABASE_DIR, 'app.db')}"
    )

    # Connection pooling configuration
    # Note: SQLite has limited connection pooling support
    # These settings are more relevant for PostgreSQL/MySQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('DB_POOL_SIZE', 10)),
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 20)),
        'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', 30)),
        'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', 3600)),
        'pool_pre_ping': os.environ.get('DB_POOL_PRE_PING', 'True').lower() == 'true',
    }

    # Redis cache configuration
    REDIS_ENABLED = os.environ.get('REDIS_ENABLED', 'False').lower() == 'true'
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
    REDIS_DECODE_RESPONSES = True

    # Cache configuration
    CACHE_TYPE = 'redis' if REDIS_ENABLED else 'memory'
    CACHE_DEFAULT_TTL = int(os.environ.get('CACHE_DEFAULT_TTL', 300))  # 5 minutes
    CACHE_SETTINGS_TTL = int(os.environ.get('CACHE_SETTINGS_TTL', 600))  # 10 minutes

    # Query performance monitoring
    QUERY_MONITOR_ENABLED = os.environ.get('QUERY_MONITOR_ENABLED', 'True').lower() == 'true'
    SLOW_QUERY_THRESHOLD = float(os.environ.get('SLOW_QUERY_THRESHOLD', 0.5))  # seconds

    # Uploads configuration
    UPLOAD_ROOT = os.environ.get('UPLOAD_ROOT', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads'))
    UPLOAD_DIR = UPLOAD_ROOT

    # Backup configuration
    BACKUP_DIR = os.environ.get('BACKUP_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups'))
    BACKUP_RETENTION_COUNT = int(os.environ.get('BACKUP_RETENTION_COUNT', 10))
    AUTO_BACKUP_ENABLED = os.environ.get('AUTO_BACKUP_ENABLED', 'False').lower() == 'true'

    # CORS configuration
    ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',')

    # Default values for alarm generation
    DEFAULT_ALARM_MIN_VERSION = os.environ.get('DEFAULT_ALARM_MIN_VERSION', '11.6.14')
    DEFAULT_ASSIGNEE_ID = int(os.environ.get('DEFAULT_ASSIGNEE_ID', 655372))
    DEFAULT_ESC_ASSIGNEE_ID = int(os.environ.get('DEFAULT_ESC_ASSIGNEE_ID', 90118))

    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

    # Disable query monitoring in development by default (can be noisy)
    QUERY_MONITOR_ENABLED = os.environ.get('QUERY_MONITOR_ENABLED', 'False').lower() == 'true'

    # Shorter cache TTL for development
    CACHE_DEFAULT_TTL = 60
    CACHE_SETTINGS_TTL = 120


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

    # Force HTTPS in production
    PREFERRED_URL_SCHEME = 'https'

    # Production database (PostgreSQL or MySQL recommended)
    # Example PostgreSQL:
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://user:pass@localhost/dbname')

    # Enhanced connection pooling for production
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('DB_POOL_SIZE', 20)),
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 40)),
        'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', 30)),
        'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', 1800)),
        'pool_pre_ping': True,
    }

    # Enable Redis cache in production
    REDIS_ENABLED = os.environ.get('REDIS_ENABLED', 'True').lower() == 'true'
    CACHE_TYPE = 'redis' if REDIS_ENABLED else 'memory'

    # Longer cache TTL for production
    CACHE_DEFAULT_TTL = 600  # 10 minutes
    CACHE_SETTINGS_TTL = 1800  # 30 minutes

    # Enable query monitoring in production
    QUERY_MONITOR_ENABLED = True
    SLOW_QUERY_THRESHOLD = 0.3  # More aggressive threshold

    # Enable automatic backups in production
    AUTO_BACKUP_ENABLED = True
    BACKUP_RETENTION_COUNT = 30


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True

    # Use in-memory database for tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

    # Use temporary directories for tests
    UPLOAD_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests', 'uploads')
    UPLOAD_DIR = UPLOAD_ROOT
    BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests', 'backups')

    # Disable caching in tests
    CACHE_TYPE = 'memory'
    CACHE_DEFAULT_TTL = 0
    CACHE_SETTINGS_TTL = 0

    # Disable query monitoring in tests
    QUERY_MONITOR_ENABLED = False

    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_redis_connection():
    """
    Get Redis connection if enabled

    Returns:
        Redis client instance or None
    """
    config_name = os.getenv('FLASK_CONFIG', 'default')
    config_obj = config[config_name]

    if not config_obj.REDIS_ENABLED:
        return None

    try:
        import redis

        client = redis.Redis(
            host=config_obj.REDIS_HOST,
            port=config_obj.REDIS_PORT,
            db=config_obj.REDIS_DB,
            password=config_obj.REDIS_PASSWORD,
            decode_responses=config_obj.REDIS_DECODE_RESPONSES
        )

        # Test connection
        client.ping()
        return client

    except ImportError:
        print("Warning: redis package not installed. Install with: pip install redis")
        return None
    except Exception as e:
        print(f"Warning: Failed to connect to Redis: {e}")
        return None
