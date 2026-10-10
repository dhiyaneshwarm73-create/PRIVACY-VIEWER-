# AI Privacy Viewer 🛡️👁️

An intelligent, real-time desktop privacy protection system powered by Computer Vision and Deep Learning.

---

## 🎯 Project Overview

**AI Privacy Viewer** safeguards your desktop screen from unauthorized viewers ("shoulder surfers"). Using the computer's webcam, the system detects human faces in real-time, identifies authorized vs. unknown people using 3-tier matching, tracks gaze orientation, and automatically triggers visual screen privacy shields (opaque modal or blurred desktop background) when an unauthorized onlooker or multiple people are detected.

---

## ⚡ Performance Optimizations & Architecture

- **Decoupled Capture & Inference**: A dedicated hardware capture thread grabs frames at 30+ FPS and feeds a bounded queue (`maxsize=1`), instantly discarding stale frames to eliminate buffer backlog and latency.
- **Downscaled Inference (3x CPU Speedup)**: Face detection runs on an optimized inference resolution (e.g. 320px) while preserving full native resolution for crystal-clear video preview and bounding box overlays.
- **Intermittent Inference Scheduling**: YOLO detection and Facenet embeddings run with configurable frame skipping and temporal smoothing, keeping the UI silky smooth without sacrificing security.
- **Latency & FPS Profiling**: Measures and displays exact webcam capture FPS, AI inference latency (ms), and end-to-end frame processing time in real-time on the dashboard.
- **Safe Resource Lifecycle**: Robust thread teardown and hardware release on camera stop or application exit.

---

## 👤 Local Face Registration & 3-Tier Recognition

- **Live Multi-Sample Capture Dialog**: Interactive modal with alignment guide, face size verification, lighting checks, and explicit user consent to capture 3–5 diverse facial angles.
- **Persistent Local Embeddings**: Biometric embeddings are generated locally via FaceNet (DeepFace) and stored in `data/authorized_embeddings.json` for instantaneous startup without re-encoding disk images.
- **3-Tier Identity Classification**:
  - **AUTHORIZED**: Confirmed identity (cosine distance $\le 0.38$, confidence $\ge 70\%$).
  - **UNCERTAIN**: Suspicious/ambiguous match ($0.38 < \text{distance} \le 0.52$). Never falsely authorizes.
  - **UNKNOWN**: Unauthorized viewer ($\text{distance} > 0.52$).
  - **NO_REGISTERED_USERS**: When no profiles have been registered yet.
- **100% Offline & Private**: No biometric data or video frames ever leave your local device. Biometrics and embeddings are strictly excluded in `.gitignore`.

---

## 🛡️ Screen-Wide Privacy Protection

- **Windows-Compatible Fullscreen Overlay**: Top-level, frameless, always-on-top window (`Qt.WindowStaysOnTopHint`) that covers the primary display to shield desktop applications from onlookers.
- **Two Visual Shield Modes**:
  - **High-Contrast Opaque Shield**: Deep dark glassmorphism card with warning badges and threat descriptions.
  - **Blurred Desktop Snapshot Background**: One-shot desktop capture with Gaussian blur applied strictly *before* overlay presentation to eliminate self-capture recursion loops.
- **Intelligent Threat Debouncing**:
  - Activates when an unknown/uncertain viewer is seen for consecutive frames (e.g., 3 frames).
  - Activates when multiple faces are detected (shoulder-surfing protection).
  - Optional look-away protection if the owner turns away from the screen for > 3.0s.
  - Configurable recovery delay (e.g., 1.2s) before dismissing shield to eliminate screen flickering.
- **Safe Owner Dismissal**: Dismissable at any time via Escape key (`Esc`), Dismiss button, or when the owner's face is confirmed.

---

## 🖥️ Desktop User Interface

The desktop dashboard is built with **PySide6 (Qt6)** featuring a modern dark theme:
1. **📊 Dashboard**: Live camera preview, real-time FPS & AI latency metrics, 3-tier status badges (Webcam, YOLO, 3-Tier Recognition, MediaPipe Gaze, Desktop Shield), and control buttons.
2. **👤 Face Registration**: Live camera multi-sample capture dialog, photo upload option, and enrolled identity table with deletion.
3. **📜 Activity Logs**: Real-time security event audit log showing timestamps, logging levels, and privacy trigger actions.
4. **⚙️ Settings**: Adjustable detection confidence, inference downscaling width, recognition thresholds, look-away delays, and screen overlay options.

---

## 🚀 Getting Started on Windows

### 1. Prerequisites
- **Python 3.11** (Recommended & Verified)
- Webcam (built-in or USB external)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch Desktop Application
```bash
python run.py
```

### 4. Run Test Suite
```bash
python tests/test_performance_pipeline.py
python tests/test_privacy_engine.py
python tests/test_privacy_overlay.py
python tests/test_face_detection.py
python tests/test_face_recognition.py
python tests/test_gaze_tracking.py
python tests/test_ui_smoke.py
```

---

## 🔒 Security & Privacy Statement
- All image processing occurs **100% locally** on your machine.
- No webcam frames, biometric vectors, or facial images are uploaded to any external server or cloud service.
- Biometric vectors and raw images are excluded from logs and git tracking.

