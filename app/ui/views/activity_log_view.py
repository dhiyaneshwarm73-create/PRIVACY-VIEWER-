"""
Live Activity and Security Events Log View.
"""

from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.utils.logger import setup_logger

logger = setup_logger("ActivityLogView")


class ActivityLogView(QWidget):
    """
    Displays real-time operational and security events in a searchable table.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_logs = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # 1. Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        
        title = QLabel("Security & System Activity Logs")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #f8fafc;")
        
        subtitle = QLabel("Real-time audit log of camera sessions, face detections, and privacy shield events.")
        subtitle.setStyleSheet("font-size: 13px; color: #94a3b8;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        # 2. Filter & Actions Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("🔍 Filter logs by keyword, level, or component...")
        self.input_search.textChanged.connect(self.filter_logs)

        self.btn_clear = QPushButton("🗑️ Clear Logs")
        self.btn_clear.clicked.connect(self.clear_logs)

        toolbar.addWidget(self.input_search, stretch=3)
        toolbar.addWidget(self.btn_clear, stretch=1)
        main_layout.addLayout(toolbar)

        # 3. Log Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Level", "Component", "Message"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        main_layout.addWidget(self.table, stretch=1)

        # Prepopulate with system startup log
        self.add_log("INFO", "System", "Application initialized and user interface loaded.")

    def add_log(self, level: str, component: str, message: str):
        """Append a new log entry to the table."""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = (now_str, level, component, message)
        self.all_logs.append(entry)

        # Check if search filter matches
        search_text = self.input_search.text().lower()
        if not search_text or any(search_text in str(col).lower() for col in entry):
            self._insert_row(entry)

    def _insert_row(self, entry):
        now_str, level, component, message = entry
        row = self.table.rowCount()
        self.table.insertRow(row)

        item_time = QTableWidgetItem(now_str)
        item_level = QTableWidgetItem(level)
        item_comp = QTableWidgetItem(component)
        item_msg = QTableWidgetItem(message)

        # Color-code level
        if level == "ERROR":
            item_level.setForeground(Qt.red)
        elif level == "WARNING":
            item_level.setForeground(Qt.yellow)
        elif level == "INFO":
            item_level.setForeground(Qt.cyan)

        self.table.setItem(row, 0, item_time)
        self.table.setItem(row, 1, item_level)
        self.table.setItem(row, 2, item_comp)
        self.table.setItem(row, 3, item_msg)
        self.table.scrollToBottom()

    def filter_logs(self, text: str):
        """Filter table rows by search text."""
        self.table.setRowCount(0)
        search_text = text.lower()
        for entry in self.all_logs:
            if not search_text or any(search_text in str(col).lower() for col in entry):
                self._insert_row(entry)

    def clear_logs(self):
        """Clear all visible and stored log items."""
        self.all_logs.clear()
        self.table.setRowCount(0)
