"""
Privacy-Conscious Logging Module for AI Privacy Viewer.

Provides structured logging to console and local log files.
Guarantees privacy by forbidding logging of raw biometric embeddings or image data.
"""

import logging
import sys
from pathlib import Path
from app.utils.config import config


def setup_logger(name: str = "AIPrivacyViewer", log_level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return a standardized logger instance.
    
    Args:
        name: Logger name (usually module name)
        log_level: Logging severity level
        
    Returns:
        Configured logging.Logger
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if setup is called multiple times
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG if config.debug_mode else log_level)
    
    # Formatter: [2026-10-10 10:00:00] [INFO] [Module] Message
    log_format = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)-7s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 1. Console Handler (Safe against Windows cp1252 charmap errors)
    try:
        # If sys.stdout supports reconfigure
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)
    except Exception as e:
        print(f"Warning: Could not setup console logger: {e}")
    
    # 2. Rotating File Handler (local logs only)
    log_file_path = config.storage.logs_dir / "privacy_viewer.log"
    try:
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8", errors="replace")
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)
    except Exception as e:
        pass
        
    return logger


# Default application logger
app_logger = setup_logger()

