"""
Main Application Entry Point for AI Privacy Viewer.

Coordinates system initialization, configuration loading, and launches the PySide6 Desktop GUI.
"""

import sys
import platform
from pathlib import Path

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
    logger.info("Initializing AI Privacy Viewer Desktop UI...")
    
    if not run_system_check():
        logger.error("Initialization failed during system check.")
        sys.exit(1)

    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QFont
        from app.ui.main_window import MainWindow
    except ImportError as e:
        logger.error(f"PySide6 is not installed: {e}")
        print("\n[ERROR] PySide6 is required to display the desktop interface.")
        print("Please run: pip install PySide6\n")
        sys.exit(1)

    # Initialize Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName(config.app_name)
    app.setOrganizationName("AIPrivacyViewer")

    # Set default modern application font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Instantiate and display main window
    window = MainWindow()
    window.show()
    
    logger.info("AI Privacy Viewer Desktop GUI launched successfully.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
