import logging
import sys

# Global flag to track if logging is configured
_logging_configured = False

class CustomFormatter(logging.Formatter):
    # ANSI escape codes for colors
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    green = "\x1b[32;20m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
def setup_logger(name='myapp', level=logging.DEBUG):
    """Set up logger with consistent formatting across modules"""
    global _logging_configured
    
    # Configure root logger to avoid duplicates
    root_logger = logging.getLogger()
    
    # Clear existing handlers to prevent duplicates
    if not _logging_configured:
        root_logger.handlers.clear()
        
        # Set up root logger
        root_logger.setLevel(level)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        # Use CustomFormatter for colored logs
        console_handler.setFormatter(CustomFormatter())
        
        # Add handler to root logger
        root_logger.addHandler(console_handler)
        
        # Mark as configured
        _logging_configured = True
    
    # Return named logger that will use root logger's configuration
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    return logger