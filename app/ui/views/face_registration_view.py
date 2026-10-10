"""
Face Registration and Profile Management View.

Enables local face enrollment via live webcam multi-sample capture or photo upload,
generates normalized local face embeddings, and manages enrolled identities with zero cloud leakage.
"""

import time
from pathlib import Path
from typing import List, Optional
import cv2
import numpy as np
from PySide6.QtCore import QSize, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QFont, QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ai.face_detection import FaceDetector
from app.ai.face_recognition import FaceRecognizer
from app.utils.config import config
from app.utils.logger import setup_logger

logger = setup_logger("FaceRegistrationView")


class LiveFaceCaptureDialog(QDialog):
    """
    Interactive modal dialog that captures multiple high-quality face samples
    from the webcam with real-time feedback and explicit user consent.
    """
    samples_captured = Signal(list)  # List of numpy face crops

    def __init__(self, user_name: str, target_samples: int = 3, parent=None):
        super().__init__(parent)
        self.user_name = user_name
        self.target_samples = target_samples
        self.captured_crops: List[np.ndarray] = []
        self.detector = FaceDetector()
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.timer: Optional[QTimer] = None
        self.current_frame: Optional[np.ndarray] = None
        self.current_bbox: Optional[List[int]] = None
        
        self.setWindowTitle(f"Enroll Face — {self.user_name}")
        self.setFixedSize(620, 600)
        self.init_ui()
        self.start_camera()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Title
        lbl_title = QLabel(f"Face Sample Acquisition: {self.user_name}")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #f8fafc;")
        layout.addWidget(lbl_title)

        lbl_instruct = QLabel("Position your face within the frame in good lighting. Click 'Capture Sample' to record 3 diverse angles.")
        lbl_instruct.setStyleSheet("font-size: 12px; color: #94a3b8;")
        lbl_instruct.setWordWrap(True)
        layout.addWidget(lbl_instruct)

        # Camera View
        self.video_label = QLabel()
        self.video_label.setFixedSize(580, 360)
        self.video_label.setStyleSheet("background-color: #000000; border: 2px solid #334155; border-radius: 8px;")
        self.video_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.video_label)

        # Quality / Status Prompt
        self.lbl_feedback = QLabel("Searching for face...")
        self.lbl_feedback.setStyleSheet("font-size: 13px; font-weight: 600; color: #38bdf8;")
        self.lbl_feedback.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_feedback)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self.target_samples)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Samples Captured: %v / %m")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                text-align: center;
                color: #ffffff;
                font-weight: 600;
                height: 22px;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Consent Checkbox
        self.chk_consent = QCheckBox("I consent to capturing local biometric face embeddings for screen privacy protection.")
        self.chk_consent.setChecked(True)
        self.chk_consent.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        layout.addWidget(self.chk_consent)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_capture = QPushButton("📸 Capture Face Sample (1/3)")
        self.btn_capture.setObjectName("PrimaryButton")
        self.btn_capture.setFixedHeight(40)
        self.btn_capture.clicked.connect(self.capture_sample)

        self.btn_finish = QPushButton("✓ Save & Enroll")
        self.btn_finish.setEnabled(False)
        self.btn_finish.setFixedHeight(40)
        self.btn_finish.clicked.connect(self.finish_enrollment)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setFixedHeight(40)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_capture, stretch=2)
        btn_layout.addWidget(self.btn_finish, stretch=2)
        btn_layout.addWidget(self.btn_cancel, stretch=1)
        layout.addLayout(btn_layout)

    def start_camera(self):
        self.cap = cv2.VideoCapture(config.camera.camera_index, cv2.CAP_DSHOW)
        if not self.cap or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(config.camera.camera_index)
            
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_feed)
        self.timer.start(33)  # ~30 FPS

    def update_feed(self):
        if self.cap is None or not self.cap.isOpened():
            self.video_label.setText("Camera Unavailable")
            return

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return

        self.current_frame = frame.copy()
        
        # Detect face
        detections = self.detector.detect_faces(frame, use_inference_scaling=True)
        faces = detections.get("faces", [])
        
        annotated = self.detector.draw_detections(frame, detections)
        
        if len(faces) == 1:
            self.current_bbox = faces[0]["bbox"]
            fw = self.current_bbox[2] - self.current_bbox[0]
            fh = self.current_bbox[3] - self.current_bbox[1]
            if fw >= config.recognition.min_face_size and fh >= config.recognition.min_face_size:
                self.lbl_feedback.setText("✓ Face positioned well. Ready to capture!")
                self.lbl_feedback.setStyleSheet("font-size: 13px; font-weight: 600; color: #10b981;")
                self.btn_capture.setEnabled(True)
            else:
                self.lbl_feedback.setText("⚠️ Please move closer to the camera.")
                self.lbl_feedback.setStyleSheet("font-size: 13px; font-weight: 600; color: #f59e0b;")
        elif len(faces) > 1:
            self.lbl_feedback.setText("⚠️ Multiple faces detected! Only 1 person should be in view.")
            self.lbl_feedback.setStyleSheet("font-size: 13px; font-weight: 600; color: #ef4444;")
            self.current_bbox = None
        else:
            self.lbl_feedback.setText("No face detected. Please face the camera.")
            self.lbl_feedback.setStyleSheet("font-size: 13px; font-weight: 600; color: #94a3b8;")
            self.current_bbox = None

        # Convert to QPixmap
        rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qimg).scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def capture_sample(self):
        if not self.chk_consent.isChecked():
            QMessageBox.warning(self, "Consent Required", "Please confirm user consent to enroll face biometrics.")
            return

        if self.current_frame is None or self.current_bbox is None:
            QMessageBox.warning(self, "No Face Detected", "Please ensure your face is clearly visible in the camera before capturing.")
            return

        crop = FaceDetector.extract_face_crop(self.current_frame, self.current_bbox)
        if crop is None or crop.size == 0:
            QMessageBox.warning(self, "Invalid Sample", "Could not crop face region. Please try again.")
            return

        self.captured_crops.append(crop)
        count = len(self.captured_crops)
        self.progress_bar.setValue(count)

        if count < self.target_samples:
            self.btn_capture.setText(f"📸 Capture Face Sample ({count + 1}/{self.target_samples})")
            self.lbl_feedback.setText(f"Sample {count} captured! Slightly tilt head and take sample {count + 1}.")
        else:
            self.btn_capture.setEnabled(False)
            self.btn_finish.setEnabled(True)
            self.btn_finish.setStyleSheet("background-color: #10b981; color: white; font-weight: bold;")
            self.lbl_feedback.setText(f"All {self.target_samples} samples captured! Click 'Save & Enroll'.")

    def finish_enrollment(self):
        if not self.captured_crops:
            QMessageBox.warning(self, "No Samples", "Please capture at least one face sample.")
            return
        self.samples_captured.emit(self.captured_crops)
        self.accept()

    def closeEvent(self, event):
        if self.timer is not None:
            self.timer.stop()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        event.accept()


class FaceRegistrationView(QWidget):
    """
    Enables user face enrollment, profile listing, and deletion.
    """
    face_registered = Signal(str, str)  # (name, file_path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.recognizer = FaceRecognizer()
        self.init_ui()
        self.refresh_profiles()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # 1. Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        
        title = QLabel("Face Registration & Authorization")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #f8fafc;")
        
        subtitle = QLabel("Enroll trusted user faces for local 3-tier authentication. Embeddings remain strictly on your local device.")
        subtitle.setStyleSheet("font-size: 13px; color: #94a3b8;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        # 2. Registration Card
        enroll_card = QFrame()
        enroll_card.setProperty("class", "CardWidget")
        enroll_layout = QVBoxLayout(enroll_card)
        enroll_layout.setContentsMargins(20, 20, 20, 20)
        enroll_layout.setSpacing(14)

        card_title = QLabel("ENROLL NEW AUTHORIZED USER")
        card_title.setProperty("class", "CardTitle")
        enroll_layout.addWidget(card_title)

        form_layout = QHBoxLayout()
        form_layout.setSpacing(12)

        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Enter full name / identifier (e.g., John Doe)...")
        self.input_name.setMinimumHeight(38)

        self.btn_live_capture = QPushButton("📷 Capture Face (Live Camera)")
        self.btn_live_capture.setObjectName("PrimaryButton")
        self.btn_live_capture.setMinimumHeight(38)
        self.btn_live_capture.clicked.connect(self.open_live_capture)

        self.btn_upload = QPushButton("📁 Upload Photo")
        self.btn_upload.setMinimumHeight(38)
        self.btn_upload.clicked.connect(self.upload_photo)

        form_layout.addWidget(self.input_name, stretch=3)
        form_layout.addWidget(self.btn_live_capture, stretch=2)
        form_layout.addWidget(self.btn_upload, stretch=1)
        enroll_layout.addLayout(form_layout)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 12px; color: #10b981;")
        enroll_layout.addWidget(self.status_label)

        main_layout.addWidget(enroll_card)

        # 3. Registered Profiles Table Card
        table_card = QFrame()
        table_card.setProperty("class", "CardWidget")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(20, 20, 20, 20)
        table_layout.setSpacing(12)

        table_header = QHBoxLayout()
        table_title = QLabel("AUTHORIZED USERS DATABASE")
        table_title.setProperty("class", "CardTitle")
        
        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.clicked.connect(self.refresh_profiles)
        
        table_header.addWidget(table_title)
        table_header.addStretch()
        table_header.addWidget(self.btn_refresh)
        table_layout.addLayout(table_header)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name / ID", "Samples Enrolled", "Registration Date", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        table_layout.addWidget(self.table)
        main_layout.addWidget(table_card, stretch=1)

    def open_live_capture(self):
        """Open the live face sample acquisition modal dialog."""
        name = self.input_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Name", "Please enter a user name or identifier before capturing face samples.")
            return

        dialog = LiveFaceCaptureDialog(user_name=name, target_samples=config.recognition.sample_count_for_enrollment, parent=self)
        dialog.samples_captured.connect(lambda crops: self.on_samples_captured(name, crops))
        dialog.exec()

    def on_samples_captured(self, name: str, face_crops: List[np.ndarray]):
        """Process captured crops, compute embeddings, and store locally."""
        self.status_label.setStyleSheet("color: #38bdf8;")
        self.status_label.setText(f"Computing local embeddings for '{name}'...")
        
        success, msg = self.recognizer.register_identity(name, face_crops, user_consent=True)
        if success:
            self.status_label.setStyleSheet("color: #10b981;")
            self.status_label.setText(f"✓ {msg}")
            self.input_name.clear()
            self.refresh_profiles()
            self.face_registered.emit(name, str(config.storage.authorized_faces_dir / f"{name}.jpg"))
        else:
            self.status_label.setStyleSheet("color: #ef4444;")
            self.status_label.setText(f"Registration Error: {msg}")
            QMessageBox.critical(self, "Registration Error", msg)

    def upload_photo(self):
        """Allow user to select an existing face image to register."""
        name = self.input_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Name", "Please enter a user name before selecting an image.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Face Image",
            "",
            "Images (*.jpg *.jpeg *.png *.bmp *.webp)"
        )
        if not file_path:
            return

        self.status_label.setStyleSheet("color: #38bdf8;")
        self.status_label.setText(f"Extracting features from '{Path(file_path).name}'...")

        success, msg = self.recognizer.register_identity(name, file_path, user_consent=True)
        if success:
            self.status_label.setStyleSheet("color: #10b981;")
            self.status_label.setText(f"✓ {msg}")
            self.input_name.clear()
            self.refresh_profiles()
            self.face_registered.emit(name, file_path)
            logger.info(f"User enrolled from file: {name}")
        else:
            self.status_label.setStyleSheet("color: #ef4444;")
            self.status_label.setText(f"Failed to register image: {msg}")
            logger.error(f"Error registering face image: {msg}")

    def refresh_profiles(self):
        """Reload profiles from FaceRecognizer and populate table."""
        self.recognizer.reload_authorized_users()
        profiles = self.recognizer.get_registered_profiles()
        
        self.table.setRowCount(len(profiles))
        for row, profile in enumerate(profiles):
            name = profile["name"]
            sample_cnt = f"{profile.get('sample_count', 1)} sample(s)"
            reg_date = profile.get("registered_at", "N/A")

            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(sample_cnt))
            self.table.setItem(row, 2, QTableWidgetItem(reg_date))

            btn_del = QPushButton("Delete")
            btn_del.setObjectName("DangerButton")
            btn_del.setFixedWidth(70)
            btn_del.clicked.connect(lambda _, n=name: self.delete_profile(n))
            self.table.setCellWidget(row, 3, btn_del)

    def delete_profile(self, name: str):
        """Delete an enrolled authorized identity."""
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete profile '{name}' from the authorized database?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            success = self.recognizer.delete_identity(name)
            if success:
                self.status_label.setStyleSheet("color: #10b981;")
                self.status_label.setText(f"Profile '{name}' deleted.")
                self.refresh_profiles()
            else:
                QMessageBox.critical(self, "Error", f"Failed to delete profile '{name}'.")

