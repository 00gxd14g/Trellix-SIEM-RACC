import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from models.customer import db
from routes.customer import customer_bp
from routes.rule import rule_bp
from routes.alarm import alarm_bp
from routes.analysis import analysis_bp
from routes.logs import logs_bp
from routes.settings import settings_bp
from config import config
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from utils.request_logger import request_logger_middleware

def setup_logging(app):
    """Setup logging configuration"""
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # File handler for all logs
    file_handler = RotatingFileHandler(
        'logs/trellix-api.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(funcName)s(): %(message)s'
    ))
    file_handler.setLevel(logging.DEBUG)
    
    # Error file handler
    error_file_handler = RotatingFileHandler(
        'logs/trellix-api-error.log',
        maxBytes=10485760,
        backupCount=10
    )
    error_file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(funcName)s() Line:%(lineno)d: %(message)s'
    ))
    error_file_handler.setLevel(logging.ERROR)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # DB Handler for Audit Logs
    from utils.db_log_handler import DBLogHandler
    db_handler = DBLogHandler()
    db_handler.setLevel(logging.DEBUG)
    
    # Add handlers to app logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_file_handler)
    app.logger.addHandler(console_handler)
    app.logger.addHandler(db_handler)
    
    app.logger.setLevel(logging.DEBUG) # Enable DEBUG level for app logger
    
    # Also attach to root logger to capture logs from other modules
    logging.getLogger().addHandler(db_handler)
    logging.getLogger().setLevel(logging.DEBUG)

    app.logger.info('Trellix API logging started')

def create_app(config_name='default'):
    # Set static folder to frontend dist directory for production
    static_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist', 'assets')
    static_url_path = '/assets'

    app = Flask(__name__, static_folder=static_folder, static_url_path=static_url_path)
    app.config.from_object(config[config_name])
    
    # Setup logging
    setup_logging(app)

    # CORS Configuration
    if config_name == 'production':
        cors_origins = app.config.get('ALLOWED_ORIGINS', [])
    else:
        cors_origins = "*"

    CORS(app, resources={
        r"/api/*": {
            "origins": cors_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Customer-ID"],
            "supports_credentials": True
        }
    })

    # Initialize extensions
    db.init_app(app)

    # Create directories
    with app.app_context():
        if not os.path.exists(app.config['DATABASE_DIR']):
            os.makedirs(app.config['DATABASE_DIR'])
        if not os.path.exists(app.config['UPLOAD_DIR']):
            os.makedirs(app.config['UPLOAD_DIR'])
        db.create_all()
        
        # Enable WAL (Write-Ahead Logging) mode for SQLite to prevent database locked errors
        if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
            from sqlalchemy import event, text
            
            @event.listens_for(db.engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA busy_timeout=30000")  # 30 seconds
                cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
                cursor.close()
            
            # Trigger the event for existing connection
            with db.engine.connect() as conn:
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.execute(text("PRAGMA synchronous=NORMAL"))
                conn.execute(text("PRAGMA busy_timeout=30000"))
                conn.commit()
            
            app.logger.info('SQLite WAL mode enabled for better concurrent performance')

    # Register blueprints
    app.register_blueprint(customer_bp, url_prefix='/api')
    app.register_blueprint(rule_bp, url_prefix='/api')
    app.register_blueprint(alarm_bp, url_prefix='/api')
    app.register_blueprint(analysis_bp, url_prefix='/api')
    app.register_blueprint(logs_bp, url_prefix='/api')
    app.register_blueprint(settings_bp, url_prefix='/api')
    
    # Setup request/response logging middleware
    request_logger_middleware(app)
    
    # Swagger UI route
    @app.route('/api/docs')
    def swagger_ui():
        # Return simple HTML with embedded Swagger UI
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>RACC API Documentation</title>
            <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui.css" />
            <style>
                body { margin: 0; }
                .swagger-ui .topbar { display: none; }
            </style>
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui-bundle.js"></script>
            <script src="https://unpkg.com/swagger-ui-dist@4.5.0/swagger-ui-standalone-preset.js"></script>
            <script>
            window.onload = function() {
                const ui = SwaggerUIBundle({
                    url: "/api/swagger.json",
                    dom_id: '#swagger-ui',
                    deepLinking: true,
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIStandalonePreset
                    ],
                    plugins: [
                        SwaggerUIBundle.plugins.DownloadUrl
                    ],
                    layout: "StandaloneLayout"
                })
                window.ui = ui
            }
            </script>
        </body>
        </html>
        '''

    @app.route('/api/swagger.json')
    def swagger_json():
        """Serve swagger.json file"""
        swagger_doc = {
            "swagger": "2.0",
            "info": {
                "title": "RACC API",
                "description": "Rule & Alarm Control Center API for Trellix SIEM",
                "version": "2.0.0"
            },
            "host": "localhost:5000",
            "basePath": "/api",
            "schemes": ["http", "https"],
            "consumes": ["application/json"],
            "produces": ["application/json"],
            "paths": {
                "/health": {
                    "get": {
                        "summary": "Health check endpoint",
                        "responses": {
                            "200": {
                                "description": "API is healthy",
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "message": {"type": "string"},
                                        "version": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                },
                "/customers": {
                    "get": {
                        "summary": "Get all customers",
                        "responses": {
                            "200": {
                                "description": "List of customers",
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "success": {"type": "boolean"},
                                        "customers": {
                                            "type": "array",
                                            "items": {"$ref": "#/definitions/Customer"}
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "post": {
                        "summary": "Create a new customer",
                        "parameters": [{
                            "in": "body",
                            "name": "customer",
                            "schema": {
                                "type": "object",
                                "required": ["name"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "contact_email": {"type": "string"},
                                    "contact_phone": {"type": "string"}
                                }
                            }
                        }],
                        "responses": {
                            "201": {
                                "description": "Customer created",
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "success": {"type": "boolean"},
                                        "customer": {"$ref": "#/definitions/Customer"}
                                    }
                                }
                            }
                        }
                    }
                },
                "/customers/{id}": {
                    "get": {
                        "summary": "Get customer by ID",
                        "parameters": [{
                            "name": "id",
                            "in": "path",
                            "type": "integer",
                            "required": True
                        }],
                        "responses": {
                            "200": {
                                "description": "Customer details",
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "success": {"type": "boolean"},
                                        "customer": {"$ref": "#/definitions/Customer"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "definitions": {
                "Customer": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "contact_email": {"type": "string"},
                        "contact_phone": {"type": "string"},
                        "created_at": {"type": "string", "format": "date-time"},
                        "updated_at": {"type": "string", "format": "date-time"},
                        "rule_count": {"type": "integer"},
                        "alarm_count": {"type": "integer"},
                        "file_count": {"type": "integer"}
                    }
                }
            }
        }
        return jsonify(swagger_doc)

    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return {
            'status': 'healthy',
            'message': 'RACC API is running',
            'version': '2.0.0'
        }

    # Serve frontend index.html for production
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        """Serve frontend files in production"""
        # Check if path is an API route
        if path.startswith('api/'):
            return jsonify({'error': 'API endpoint not found'}), 404

        # Check if path is a static file (CSS, JS, etc.)
        frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')
        file_path = os.path.join(frontend_dist, path)

        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(frontend_dist, path)

        # For all other routes, serve index.html (for React Router)
        index_path = os.path.join(frontend_dist, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(frontend_dist, 'index.html')
        else:
            # If no frontend build exists, show API info
            return jsonify({
                'message': 'RACC API',
                'version': '2.0.0',
                'note': 'Frontend not built. Run: cd frontend && npm run build',
                'endpoints': {
                    'health': '/api/health',
                    'docs': '/api/docs',
                    'customers': '/api/customers',
                    'rules': '/api/customers/{id}/rules',
                    'alarms': '/api/customers/{id}/alarms',
                    'analysis': '/api/customers/{id}/analysis'
                }
            })

    from werkzeug.exceptions import Forbidden

    @app.errorhandler(Forbidden)
    def handle_forbidden(e):
        app.logger.warning(f'Forbidden access attempt: {e.description}')
        return jsonify(success=False, error=e.description), 403

    @app.errorhandler(404)
    def not_found(error):
        app.logger.warning(f'404 error: {request.url}')
        return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Internal error: {error}', exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
        
    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.error(f'Unhandled exception: {error}', exc_info=True)
        return jsonify({'success': False, 'error': str(error)}), 500

    return app

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

if __name__ == '__main__':
    print("🚀 Starting RACC API Server")
    print("📝 API Documentation: http://localhost:5000/api/docs")
    print("🔧 API Base URL: http://localhost:5000/api")
    app.run(host='0.0.0.0', port=5000, debug=True)
