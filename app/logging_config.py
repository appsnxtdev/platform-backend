import sys
import os
from pathlib import Path
from loguru import logger
from app.config import settings

# Create logs directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Remove default logger
logger.remove()

# Add console logger with color
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
)

# Add file logger for all logs
logger.add(
    "logs/app.log",
    rotation="500 MB",  # Rotate when file reaches 500MB
    retention="10 days",  # Keep logs for 10 days
    compression="zip",  # Compress rotated files
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    backtrace=True,  # Include full backtrace for errors
    diagnose=True,  # Include diagnostic information
)

# Add separate error log file
logger.add(
    "logs/error.log",
    rotation="100 MB",
    retention="30 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
    backtrace=True,
    diagnose=True,
)

# Add separate access log file for HTTP requests
logger.add(
    "logs/access.log",
    rotation="100 MB",
    retention="7 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="INFO",
    filter=lambda record: "Request:" in record["message"] or "Response:" in record["message"],
)

# Add separate audit log file for security events
logger.add(
    "logs/audit.log",
    rotation="100 MB",
    retention="90 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
    filter=lambda record: "AUDIT" in record["message"],
)

# Add environment-specific log level
if settings.SENTRY_ENVIRONMENT == "development":
    logger.add(
        "logs/debug.log",
        rotation="100 MB",
        retention="3 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        backtrace=True,
        diagnose=True,
    )

# Log startup message
logger.info(f"Starting {settings.PROJECT_NAME} in {settings.SENTRY_ENVIRONMENT} environment")
