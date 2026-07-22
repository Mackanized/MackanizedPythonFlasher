import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger(name: str, log_file: str, level=logging.DEBUG) -> logging.Logger:
    """Configures and returns a logger that writes to both file and console."""
    
    # Create the 'logs' folder if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    file_path = os.path.join("logs", log_file)

    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d | [%(levelname.upper() if hasattr(logging, "levelname") else "INFO"] | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Format with clean timestamps
    file_formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d | [%(levelname)-8s] | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    handler = RotatingFileHandler(file_path, maxBytes=0, backupCount=0, encoding='utf-8')
    handler.setFormatter(file_formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent handler duplication if the function is called multiple times
    if not logger.handlers:
        logger.addHandler(handler)

    return logger

# Global loggers for different system components
can_logger = setup_logger("CAN_TRACE", "cantrace.log")
app_logger = setup_logger("APP_DEBUG", "flasher.log")