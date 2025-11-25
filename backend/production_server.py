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
    
    # Serve the application
    serve(app, host=host, port=port)
