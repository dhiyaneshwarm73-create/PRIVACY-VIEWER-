# AI Privacy Viewer 🛡️👁️

An intelligent, real-time desktop privacy protection system powered by Computer Vision and Deep Learning.

---

## 🎯 Project Overview

**AI Privacy Viewer** safeguards your desktop screen from unauthorized viewers ("shoulder surfers"). Using the computer's webcam, the system detects human faces in real-time, identifies authorized vs. unknown people, tracks gaze orientation, and automatically triggers visual privacy shields (blur/overlay) when an unknown onlooker or multiple people are detected.

---

## 🔄 Core AI Pipeline

```text
Webcam
   ↓
OpenCV (Frame Capture)
   ↓
YOLO Face Detection (Locates faces & bounding boxes)
   ↓
DeepFace Face Recognition (Verifies authorized user vs. stranger)
   ↓
MediaPipe Gaze & Face Tracking (Estimates gaze direction)
   ↓
Privacy Decision Engine (Temporal smoothing & debouncing rules)
   ↓
Privacy View (Automatic blur / warning overlay)
   ↓
PySide6 Desktop Dashboard
```

---

## 🏗️ Architecture

```text
AI-Privacy-Viewer/
│
├── app/
│   ├── main.py                 # Application initialization and lifecycle
│   │
│   ├── ai/                     # Computer Vision & AI Modules
│   │   ├── face_detection.py   # YOLO Face Detection
│   │   ├── face_recognition.py # DeepFace User Verification
│   │   └── gaze_tracking.py    # MediaPipe Gaze Tracking
│   │
│   ├── privacy/                # Privacy Logic
│   │   ├── privacy_engine.py   # Decision Engine & Debouncing
│   │   └── privacy_view.py     # Visual Privacy Screen Overlay
│   │
│   ├── ui/                     # Desktop GUI
│   │   ├── main_window.py      # PySide6 Application Window
│   │   └── widgets.py          # Camera & Status UI Widgets
│   │
│   ├── database/               # Local Persistence
│   │   └── database.py         # SQLite Local Event Logging
│   │
│   └── utils/                  # Helper Utilities
│       ├── config.py           # Centralized Configuration & Thresholds
│       ├── logger.py           # Privacy-Conscious Logging
│       └── performance.py      # FPS & Latency Tracker
│
├── data/
│   └── authorized_faces/       # Local Face Registration Images
│
├── models/                     # Cached Pretrained Model Weights
├── tests/                      # Unit & Independent Logic Tests
├── requirements.txt            # Project Dependencies
├── .gitignore                  # Git Ignore Rules
├── README.md                   # Documentation
└── run.py                      # Application Launcher
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.11** (recommended and verified)
- Webcam (built-in or USB external)

### 2. Setup Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate on Windows
.\venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Application Check
```bash
python run.py
```

---

## 🗺️ 8-Week Milestone Roadmap

- [x] **Milestone 1:** Project Setup, Folder Structure, Config & Logging
- [ ] **Milestone 2:** OpenCV Webcam Stream Module
- [ ] **Milestone 3:** YOLO Face Detection Module
- [ ] **Milestone 4:** DeepFace Face Recognition & Registration
- [ ] **Milestone 5:** MediaPipe Gaze & Head Direction Tracking
- [ ] **Milestone 6:** Privacy Decision Engine & Temporal Debouncer
- [ ] **Milestone 7:** Visual Privacy Shield / Overlay
- [ ] **Milestone 8:** PySide6 Desktop User Interface
- [ ] **Milestone 9:** End-to-End Pipeline Integration
- [ ] **Milestone 10:** Automated Unit & Independent Pipeline Testing
- [ ] **Milestone 11:** Performance Optimization & Frame Throttling
- [ ] **Milestone 12:** Final Documentation, Presentation & Viva Preparation

---

## 🔒 Security & Privacy Statement
- All image processing occurs **100% locally** on your machine.
- No webcam frames, biometric data, or facial images are uploaded to any external server or cloud service.
- Biometric vectors and raw images are excluded from logs.
