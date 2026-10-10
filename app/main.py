"""
Main Application Entry Point for AI Privacy Viewer.

Coordinates system initialization, configuration loading, and pipeline readiness checks.
"""

import sys
import platform
from app.utils.config import config
from app.utils.logger import setup_logger

logger = setup_logger("MainApp")


def print_banner():
    banner = f"""
============================================================
              {config.app_name} - v{config.version}
       Intelligent Real-Time Desktop Privacy System
============================================================
"""
    print(banner)


def run_system_check() -> bool:
    """Check Python version, OS, and required directories."""
    logger.info(f"Python Version: {platform.python_version()} ({platform.architecture()[0]})")
    logger.info(f"Operating System: {platform.system()} {platform.release()}")
    logger.info(f"Project Root: {config.storage.data_dir.parent}")
    logger.info(f"Authorized Faces Dir: {config.storage.authorized_faces_dir}")
    logger.info(f"Models Dir: {config.storage.models_dir}")
    logger.info(f"Logs Dir: {config.storage.logs_dir}")
    
    # Check directory existence
    dirs_ready = (
        config.storage.data_dir.exists() and
        config.storage.authorized_faces_dir.exists() and
        config.storage.models_dir.exists() and
        config.storage.logs_dir.exists()
    )
    
    if dirs_ready:
        logger.info("Directory structure verified successfully.")
    else:
        logger.error("Some required directories are missing!")
        
    return dirs_ready


def main():
    print_banner()
    logger.info("Initializing AI Privacy Viewer [Milestone 1]...")
    
    success = run_system_check()
    if not success:
        logger.error("Initialization failed during system check.")
        sys.exit(1)
        
    logger.info("Milestone 1 setup is complete and fully functional.")
    logger.info("Ready for Milestone 2: OpenCV Webcam Module.")


if __name__ == "__main__":
    main()
