import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

def setup_logging():
    """Setup comprehensive logging configuration"""
    
    # Create logs directory
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging format
    log_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # Main application log file (rotating)
    app_log_file = log_dir / "autoassist_app.log"
    app_handler = logging.handlers.RotatingFileHandler(
        app_log_file, maxBytes=10*1024*1024, backupCount=5  # 10MB files, keep 5 backups
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(log_format)
    root_logger.addHandler(app_handler)
    
    # User activity log (rotating)
    activity_log_file = log_dir / "user_activity.log"
    activity_handler = logging.handlers.RotatingFileHandler(
        activity_log_file, maxBytes=5*1024*1024, backupCount=10  # 5MB files, keep 10 backups
    )
    activity_handler.setLevel(logging.INFO)
    activity_handler.setFormatter(log_format)
    
    # Create user activity logger
    user_logger = logging.getLogger("user_activity")
    user_logger.addHandler(activity_handler)
    user_logger.setLevel(logging.INFO)
    user_logger.propagate = False  # Don't send to root logger
    
    # Security/Authentication log (rotating)
    auth_log_file = log_dir / "authentication.log"
    auth_handler = logging.handlers.RotatingFileHandler(
        auth_log_file, maxBytes=5*1024*1024, backupCount=10
    )
    auth_handler.setLevel(logging.INFO)
    auth_handler.setFormatter(log_format)
    
    # Create auth logger
    auth_logger = logging.getLogger("authentication")
    auth_logger.addHandler(auth_handler)
    auth_logger.setLevel(logging.INFO)
    auth_logger.propagate = False
    
    # Error log (rotating) 
    error_log_file = log_dir / "errors.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file, maxBytes=10*1024*1024, backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(log_format)
    root_logger.addHandler(error_handler)
    
    # Chat/Messages log (rotating)
    chat_log_file = log_dir / "chat_messages.log"
    chat_handler = logging.handlers.RotatingFileHandler(
        chat_log_file, maxBytes=20*1024*1024, backupCount=10  # 20MB files for chat logs
    )
    chat_handler.setLevel(logging.INFO)
    chat_handler.setFormatter(log_format)
    
    # Create chat logger
    chat_logger = logging.getLogger("chat_messages")
    chat_logger.addHandler(chat_handler)
    chat_logger.setLevel(logging.INFO)
    chat_logger.propagate = False
    
    # API Access log (rotating)
    api_log_file = log_dir / "api_access.log"
    api_handler = logging.handlers.RotatingFileHandler(
        api_log_file, maxBytes=15*1024*1024, backupCount=7
    )
    api_handler.setLevel(logging.INFO)
    api_handler.setFormatter(log_format)
    
    # Create API logger
    api_logger = logging.getLogger("api_access")
    api_logger.addHandler(api_handler)
    api_logger.setLevel(logging.INFO)
    api_logger.propagate = False
    
    logging.info("Logging system initialized successfully")
    logging.info(f"Log files location: {log_dir}")
    
    return {
        "user_activity": user_logger,
        "authentication": auth_logger, 
        "chat_messages": chat_logger,
        "api_access": api_logger
    }

# Get specialized loggers
def get_user_logger():
    return logging.getLogger("user_activity")

def get_auth_logger():
    return logging.getLogger("authentication")

def get_chat_logger():
    return logging.getLogger("chat_messages")

def get_api_logger():
    return logging.getLogger("api_access")