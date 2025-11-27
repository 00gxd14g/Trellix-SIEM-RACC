from waitress import serve
from main import app
import os
import logging

if __name__ == "__main__":
    # Setup basic logging for the server startup
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("waitress")
    
    # Get port from environment or default to 5000
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0"
    
    logger.info(f"Starting production server on {host}:{port}")
    
    # CRITICAL FIX: Ensure SECRET_KEY is always a string, never a property object
    import secrets
    sk = app.config.get("SECRET_KEY")
    if not isinstance(sk, (str, bytes)):
        fixed = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
        app.config["SECRET_KEY"] = fixed
        app.secret_key = fixed
        logger.warning(f"SECRET_KEY was invalid ({type(sk)}). Overridden to string.")
    else:
        app.secret_key = sk
        logger.info(f"SECRET_KEY OK ({type(sk)})")
    
    # Serve the application
    serve(app, host=host, port=port)
