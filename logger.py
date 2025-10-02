"""
Logging configuration for production agent
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from config import get_settings

settings = get_settings()


def setup_logging():
    """Configure logging with file and console handlers"""

    # Create logger
    logger = logging.getLogger("agent")
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Prevent duplicate logs
    if logger.handlers:
        return logger

    # Format
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (rotating)
    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            settings.log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Global logger instance
logger = setup_logging()


def log_request(method: str, params: dict, request_id: str):
    """Log incoming request"""
    logger.info(f"Request [{request_id}] - Method: {method}")
    logger.debug(f"Request [{request_id}] - Params: {params}")


def log_response(request_id: str, status: str, duration_ms: float):
    """Log response"""
    logger.info(f"Response [{request_id}] - Status: {status} - Duration: {duration_ms:.2f}ms")


def log_error(request_id: str, error: Exception):
    """Log error"""
    logger.error(f"Error [{request_id}] - {type(error).__name__}: {str(error)}", exc_info=True)


def log_payment(cart_id: str, amount: float, currency: str, status: str):
    """Log payment event"""
    logger.info(f"Payment - CartId: {cart_id} - Amount: {amount} {currency} - Status: {status}")


def log_task(task_id: str, skill_id: str, status: str):
    """Log task event"""
    logger.info(f"Task - TaskId: {task_id} - Skill: {skill_id} - Status: {status}")
