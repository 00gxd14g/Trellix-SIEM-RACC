import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'racc-secret-key-2024')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB default

    # Database configuration
    DATABASE_DIR = os.path.join(os.path.dirname(__file__), 'database')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(DATABASE_DIR, 'app.db')}")
    
    # SQLite specific optimizations to prevent "database is locked" errors
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {
            'timeout': 30,  # Increase timeout to 30 seconds
            'check_same_thread': False,  # Allow multi-threading
        },
        'pool_pre_ping': True,  # Verify connections before using
        'pool_recycle': 3600,  # Recycle connections every hour
        'echo': False,  # Set to True for SQL debugging
    }

    # Uploads configuration
    UPLOAD_ROOT = os.environ.get('UPLOAD_ROOT', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads'))
    UPLOAD_DIR = UPLOAD_ROOT  # For backward compatibility

    # CORS configuration
    ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',')

    # Default values for alarm generation
    DEFAULT_ALARM_MIN_VERSION = os.environ.get('DEFAULT_ALARM_MIN_VERSION', '11.6.14')
    DEFAULT_ASSIGNEE_ID = int(os.environ.get('DEFAULT_ASSIGNEE_ID', 655372))
    DEFAULT_ESC_ASSIGNEE_ID = int(os.environ.get('DEFAULT_ESC_ASSIGNEE_ID', 90118))

    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    
    # Security headers
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Set to True if using HTTPS
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Ensure a strong secret key is set in production
    @property
    def SECRET_KEY(self):
        key = os.environ.get('SECRET_KEY')
        if not key:
            # Fallback to a random key if not set (warn in logs in real app)
            import secrets
            return secrets.token_hex(32)
        return key

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    # Use a temporary folder for uploads during tests
    UPLOAD_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests', 'uploads')
    UPLOAD_DIR = UPLOAD_ROOT
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
