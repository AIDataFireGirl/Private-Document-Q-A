"""
Main Application Entry Point for Private Document Q&A System.
Initializes and runs the Flask application with all components.
"""

import os
import sys
from pathlib import Path
from loguru import logger

# Flask imports
from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Local imports
from config.settings import get_config, Config
from api.routes import APIRouter
from web.routes import WebRouter


def create_app(config: Config = None) -> Flask:
    """
    Create and configure the Flask application.
    
    Args:
        config: Application configuration (optional)
        
    Returns:
        Configured Flask application
    """
    # Get configuration
    if config is None:
        config = get_config()
    
    # Create Flask app
    app = Flask(__name__)
    app.config.from_object(config)
    
    # Configure logging
    logger.add(
        config.LOGS_DIR / config.LOG_FILE,
        level=config.LOG_LEVEL,
        rotation="10 MB",
        retention="7 days"
    )
    
    # Initialize CORS
    CORS(app, resources={
        r"/api/*": {"origins": "*"},
        r"/static/*": {"origins": "*"}
    })
    
    # Initialize rate limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )
    
    # Create necessary directories
    config.create_directories()
    
    # Validate configuration
    config_errors = config.validate_config()
    if config_errors:
        logger.error(f"Configuration errors: {config_errors}")
        print(f"Configuration errors: {config_errors}")
        print("Please check your environment variables and configuration.")
        sys.exit(1)
    
    # Initialize routers
    api_router = APIRouter(app, config)
    web_router = WebRouter(app, config)
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Resource not found"}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return {"error": "Internal server error"}, 500
    
    @app.errorhandler(413)
    def too_large(error):
        return {"error": "File too large"}, 413
    
    logger.info("Application initialized successfully")
    return app


def main():
    """Main application entry point."""
    try:
        # Get configuration
        config = get_config()
        
        # Create application
        app = create_app(config)
        
        # Run the application
        logger.info(f"Starting application on port {config.PORT}")
        app.run(
            host='0.0.0.0',
            port=config.PORT,
            debug=config.FLASK_DEBUG
        )
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        print(f"Failed to start application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 