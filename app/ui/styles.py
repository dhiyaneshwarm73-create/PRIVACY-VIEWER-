"""
Modern Dark Theme Stylesheet and UI Theme Tokens for AI Privacy Viewer.
"""

DARK_THEME_QSS = """
/* ================= GLOBAL STYLES ================= */
* {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    color: #f1f5f9;
    font-size: 13px;
    box-sizing: border-box;
}

QMainWindow, QWidget#CentralWidget {
    background-color: #0b0f19;
}

/* ================= SIDEBAR NAVIGATION ================= */
#SidebarWidget {
    background-color: #0f172a;
    border-right: 1px solid #1e293b;
    min-width: 240px;
    max-width: 240px;
}

#SidebarTitleLabel {
    font-size: 18px;
    font-weight: 700;
    color: #38bdf8;
    padding: 10px 0px 2px 0px;
}

#SidebarSubtitleLabel {
    font-size: 11px;
    color: #64748b;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 1px;
}

#NavButton {
    text-align: left;
    background-color: transparent;
    border: none;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 14px;
    font-weight: 500;
    color: #94a3b8;
}

#NavButton:hover {
    background-color: #1e293b;
    color: #f8fafc;
}

#NavButton:checked {
    background-color: #1e293b;
    color: #38bdf8;
    font-weight: 600;
    border-left: 3px solid #38bdf8;
}

/* ================= HEADER BAR ================= */
#HeaderWidget {
    background-color: #0f172a;
    border-bottom: 1px solid #1e293b;
    padding: 12px 24px;
}

#HeaderTitle {
    font-size: 20px;
    font-weight: 700;
    color: #f8fafc;
}

#SystemStatusPill {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}

/* ================= CONTENT AREA & CARDS ================= */
#ContentArea {
    background-color: #0b0f19;
}

.CardWidget {
    background-color: #111827;
    border: 1px solid #1f2937;
    border-radius: 12px;
}

.CardWidget:hover {
    border-color: #374151;
}

.CardTitle {
    font-size: 12px;
    font-weight: 600;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.CardValue {
    font-size: 24px;
    font-weight: 700;
    color: #f9fafb;
}

.CardSubtext {
    font-size: 11px;
    color: #6b7280;
}

/* ================= BUTTONS ================= */
QPushButton {
    background-color: #1f2937;
    color: #f3f4f6;
    border: 1px solid #374151;
    border-radius: 8px;
    padding: 9px 18px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #374151;
    border-color: #4b5563;
}

QPushButton:pressed {
    background-color: #111827;
}

QPushButton:disabled {
    background-color: #1f2937;
    color: #4b5563;
    border-color: #1f2937;
}

QPushButton#PrimaryButton {
    background-color: #0284c7;
    border: 1px solid #0369a1;
    color: #ffffff;
}

QPushButton#PrimaryButton:hover {
    background-color: #0369a1;
    border-color: #075985;
}

QPushButton#SuccessButton {
    background-color: #059669;
    border: 1px solid #047857;
    color: #ffffff;
}

QPushButton#SuccessButton:hover {
    background-color: #047857;
}

QPushButton#DangerButton {
    background-color: #dc2626;
    border: 1px solid #b91c1c;
    color: #ffffff;
}

QPushButton#DangerButton:hover {
    background-color: #b91c1c;
}

/* ================= VIDEO PREVIEW ================= */
#VideoPreviewContainer {
    background-color: #000000;
    border: 2px solid #1f2937;
    border-radius: 12px;
}

#VideoPlaceholderLabel {
    color: #64748b;
    font-size: 15px;
    font-weight: 500;
}

/* ================= TABLES & LOGS ================= */
QTableWidget {
    background-color: #111827;
    border: 1px solid #1f2937;
    border-radius: 8px;
    gridline-color: #1f2937;
    color: #e5e7eb;
    selection-background-color: #1e293b;
    selection-color: #38bdf8;
}

QHeaderView::section {
    background-color: #1f2937;
    color: #9ca3af;
    font-weight: 600;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #374151;
}

/* ================= INPUTS & SLIDERS ================= */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #1f2937;
    border: 1px solid #374151;
    border-radius: 6px;
    padding: 8px 12px;
    color: #f9fafb;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #38bdf8;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #1f2937;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #0284c7;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #f8fafc;
    border: 2px solid #0284c7;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

/* ================= SCROLLBARS ================= */
QScrollBar:vertical {
    border: none;
    background: #0f172a;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #334155;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
