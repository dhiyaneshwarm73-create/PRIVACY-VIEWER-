"""
DeepFace-Powered Real-Time Face Recognition Module.

Encapsulates face embedding generation, 3-tier identity verification (Authorized,
Uncertain, Unknown), multi-sample local enrollment, and zero external cloud leakage.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

# Ensure UTF-8 output encoding to avoid Windows charmap issues
os.environ["PYTHONIOENCODING"] = "utf-8"

from app.utils.config import config
from app.utils.logger import setup_logger

logger = setup_logger("FaceRecognizer")


class FaceRecognizer:
    """
    Manages local face registration, embedding caching, multi-sample enrollment,
    and 3-tier real-time identity verification.
    """
    def __init__(
        self,
        model_name: Optional[str] = None,
        distance_threshold: Optional[float] = None,
        uncertain_threshold: Optional[float] = None
    ):
        self.model_name = model_name or config.recognition.model_name
        self.distance_threshold = distance_threshold or config.recognition.distance_threshold
        self.uncertain_threshold = uncertain_threshold or config.recognition.uncertain_threshold
        
        # In-memory database:
        # { "User Name": { "mean_embedding": np.ndarray, "embeddings": List[np.ndarray], "sample_count": int, "photo_file": str } }
        self.authorized_database: Dict[str, Dict[str, Any]] = {}
        
        # Recognition cache to avoid re-running heavy inference unnecessarily
        self._last_result: Dict[str, Any] = {
            "status": "NO_FACES",
            "name": None,
            "distance": 1.0,
            "confidence": 0.0
        }
        self._frame_counter = 0

        # Load registered profiles
        self.reload_authorized_users()

    def reload_authorized_users(self) -> int:
        """
        Load registered face profiles and embeddings from local storage.
        
        Returns:
            Number of registered authorized identities loaded
        """
        self.authorized_database.clear()
        auth_dir = config.storage.authorized_faces_dir
        emb_file = config.storage.embeddings_file
        
        if not auth_dir.exists():
            auth_dir.mkdir(parents=True, exist_ok=True)

        # 1. Try loading cached embeddings JSON first for instantaneous launch
        loaded_from_cache = False
        if emb_file.exists():
            try:
                with open(emb_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                for name, record in cache_data.items():
                    embs = [np.array(e, dtype=np.float32) for e in record.get("embeddings", [])]
                    if embs:
                        mean_emb = np.mean(embs, axis=0)
                        mean_emb = mean_emb / (np.linalg.norm(mean_emb) + 1e-8)
                        self.authorized_database[name] = {
                            "mean_embedding": mean_emb,
                            "embeddings": embs,
                            "sample_count": len(embs),
                            "photo_file": record.get("photo_file", f"{name}.jpg"),
                            "registered_at": record.get("registered_at", "N/A")
                        }
                if self.authorized_database:
                    loaded_from_cache = True
                    logger.info(f"Loaded {len(self.authorized_database)} profile(s) from local embedding cache.")
            except Exception as e:
                logger.warning(f"Failed to load cached embeddings: {e}. Recomputing from image files...")

        # 2. Check disk images in data/authorized_faces/
        valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        image_files = [f for f in auth_dir.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]

        # If disk has images not yet in cache, compute embeddings
        recompute_needed = False
        for img_path in image_files:
            user_name = img_path.stem.replace("_", " ").title()
            if user_name not in self.authorized_database:
                logger.info(f"Computing facial embedding for image: {img_path.name}...")
                emb = self._extract_embedding_from_file(str(img_path))
                if emb is not None:
                    norm = np.linalg.norm(emb)
                    norm_emb = emb / (norm + 1e-8)
                    self.authorized_database[user_name] = {
                        "mean_embedding": norm_emb,
                        "embeddings": [norm_emb],
                        "sample_count": 1,
                        "photo_file": img_path.name,
                        "registered_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    recompute_needed = True

        if recompute_needed or (not loaded_from_cache and self.authorized_database):
            self._save_embeddings_to_disk()

        logger.info(f"Authorized face database ready ({len(self.authorized_database)} identity profile(s)).")
        return len(self.authorized_database)

    def _save_embeddings_to_disk(self):
        """Persist current embeddings locally for fast reloads."""
        emb_file = config.storage.embeddings_file
        try:
            cache_data = {}
            for name, record in self.authorized_database.items():
                cache_data[name] = {
                    "embeddings": [e.tolist() for e in record.get("embeddings", [])],
                    "sample_count": record.get("sample_count", 1),
                    "photo_file": record.get("photo_file", ""),
                    "registered_at": record.get("registered_at", time.strftime("%Y-%m-%d %H:%M:%S"))
                }
            with open(emb_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)
            logger.info("Saved authorized face embeddings to local storage.")
        except Exception as e:
            logger.error(f"Error persisting face embeddings: {e}")

    def register_identity(
        self,
        name: str,
        face_crops_or_image_path: Any,
        user_consent: bool = True
    ) -> Tuple[bool, str]:
        """
        Enroll a new user with single or multiple face samples.
        
        Args:
            name: Full name or unique identifier
            face_crops_or_image_path: List of numpy face crops, single crop, or file path
            user_consent: Explicit user consent confirmation
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not user_consent:
            return False, "User consent is required for face registration."

        clean_name = name.strip().title()
        if not clean_name:
            return False, "Please enter a valid user name or identifier."

        extracted_embeddings: List[np.ndarray] = []
        safe_filename = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in clean_name)
        target_img_path = config.storage.authorized_faces_dir / f"{safe_filename}.jpg"

        # Case A: File path provided
        if isinstance(face_crops_or_image_path, (str, Path)):
            file_path = str(face_crops_or_image_path)
            emb = self._extract_embedding_from_file(file_path)
            if emb is None:
                return False, "Could not extract facial embedding from provided image."
            norm_emb = emb / (np.linalg.norm(emb) + 1e-8)
            extracted_embeddings.append(norm_emb)
            
            # Copy/save image
            try:
                img = cv2.imread(file_path)
                if img is not None:
                    cv2.imwrite(str(target_img_path), img)
            except Exception as e:
                logger.warning(f"Could not save reference image: {e}")

        # Case B: List of face crops (e.g. from live webcam capture)
        elif isinstance(face_crops_or_image_path, list):
            crops = face_crops_or_image_path
            if not crops:
                return False, "No face samples provided for registration."

            for i, crop in enumerate(crops):
                if crop is not None and crop.size > 0:
                    emb = self._extract_embedding_from_crop(crop)
                    if emb is not None:
                        norm_emb = emb / (np.linalg.norm(emb) + 1e-8)
                        extracted_embeddings.append(norm_emb)

            if not extracted_embeddings:
                return False, "Failed to extract clear facial features from the captured samples. Please ensure good lighting and face the camera directly."

            # Save the clearest crop as the reference photo
            try:
                cv2.imwrite(str(target_img_path), crops[0])
            except Exception as e:
                logger.warning(f"Could not save face crop image: {e}")

        # Case C: Single face crop
        elif isinstance(face_crops_or_image_path, np.ndarray):
            crop = face_crops_or_image_path
            emb = self._extract_embedding_from_crop(crop)
            if emb is None:
                return False, "Could not extract facial features from face crop."
            norm_emb = emb / (np.linalg.norm(emb) + 1e-8)
            extracted_embeddings.append(norm_emb)
            cv2.imwrite(str(target_img_path), crop)

        else:
            return False, "Invalid face input data."

        # Compute mean embedding for the identity
        mean_emb = np.mean(extracted_embeddings, axis=0)
        mean_emb = mean_emb / (np.linalg.norm(mean_emb) + 1e-8)

        # Store in database
        self.authorized_database[clean_name] = {
            "mean_embedding": mean_emb,
            "embeddings": extracted_embeddings,
            "sample_count": len(extracted_embeddings),
            "photo_file": target_img_path.name,
            "registered_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # Persist to local embeddings cache
        self._save_embeddings_to_disk()
        logger.info(f"Successfully enrolled '{clean_name}' with {len(extracted_embeddings)} sample(s).")
        return True, f"Successfully enrolled '{clean_name}' ({len(extracted_embeddings)} samples)!"

    def delete_identity(self, name: str) -> bool:
        """
        Delete an enrolled authorized face identity and associated files.
        """
        clean_name = name.strip().title()
        if clean_name not in self.authorized_database:
            # Check case-insensitive
            for k in list(self.authorized_database.keys()):
                if k.lower() == clean_name.lower():
                    clean_name = k
                    break

        if clean_name in self.authorized_database:
            record = self.authorized_database.pop(clean_name)
            photo_file = record.get("photo_file")
            if photo_file:
                p = config.storage.authorized_faces_dir / photo_file
                if p.exists():
                    try:
                        p.unlink()
                    except Exception as e:
                        logger.warning(f"Could not remove image file {p}: {e}")
            
            self._save_embeddings_to_disk()
            logger.info(f"Deleted identity '{clean_name}' from authorized database.")
            return True
        return False

    def get_registered_profiles(self) -> List[Dict[str, Any]]:
        """Return list of registered profiles for UI display."""
        profiles = []
        for name, data in self.authorized_database.items():
            profiles.append({
                "name": name,
                "sample_count": data.get("sample_count", 1),
                "photo_file": data.get("photo_file", ""),
                "registered_at": data.get("registered_at", "N/A")
            })
        return profiles

    def _extract_embedding_from_file(self, file_path: str) -> Optional[np.ndarray]:
        """Extract facial embedding from an image file."""
        try:
            from deepface import DeepFace
            embeddings = DeepFace.represent(
                img_path=file_path,
                model_name=self.model_name,
                detector_backend="skip",
                enforce_detection=False
            )
            if embeddings and "embedding" in embeddings[0]:
                raw_emb = np.array(embeddings[0]["embedding"], dtype=np.float32)
                norm = np.linalg.norm(raw_emb)
                return raw_emb / (norm + 1e-8)
        except Exception as e:
            logger.warning(f"Could not extract DeepFace embedding for {file_path}: {e}")
            
        # Fallback: Color-histogram + spatial structure feature vector
        try:
            img = cv2.imread(file_path)
            if img is not None:
                return self._extract_fallback_features(img)
        except Exception as e:
            logger.error(f"Fallback feature extraction failed: {e}")

        return None

    def _extract_embedding_from_crop(self, face_crop: np.ndarray) -> Optional[np.ndarray]:
        """Extract facial embedding from a cropped BGR numpy face array."""
        if face_crop is None or face_crop.size == 0:
            return None

        h, w = face_crop.shape[:2]
        if h < 20 or w < 20:
            return None

        try:
            from deepface import DeepFace
            rgb_crop = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
            embeddings = DeepFace.represent(
                img_path=rgb_crop,
                model_name=self.model_name,
                detector_backend="skip",
                enforce_detection=False
            )
            if embeddings and "embedding" in embeddings[0]:
                raw_emb = np.array(embeddings[0]["embedding"], dtype=np.float32)
                norm = np.linalg.norm(raw_emb)
                return raw_emb / (norm + 1e-8)
        except Exception as e:
            logger.debug(f"DeepFace crop embedding error: {e}")

        # Fallback feature vector
        try:
            return self._extract_fallback_features(face_crop)
        except Exception as e:
            logger.error(f"Fallback crop extraction error: {e}")

        return None

    def _extract_fallback_features(self, img: np.ndarray) -> np.ndarray:
        """Lightweight normalized feature descriptor fallback."""
        resized = cv2.resize(img, (96, 96))
        hist = cv2.calcHist([resized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        norm_hist = cv2.normalize(hist, hist).flatten().astype(np.float32)
        norm = np.linalg.norm(norm_hist)
        return norm_hist / (norm + 1e-8)

    def recognize_face(self, face_crop: np.ndarray) -> Dict[str, Any]:
        """
        Compare detected face crop against enrolled authorized users with 3-tier classification:
        - AUTHORIZED: Cosine distance <= distance_threshold (e.g. <= 0.38)
        - UNCERTAIN: distance_threshold < distance <= uncertain_threshold (e.g. 0.38 < dist <= 0.52)
        - UNKNOWN: distance > uncertain_threshold
        - NO_REGISTERED_USERS: When no users are enrolled

        Args:
            face_crop: Cropped BGR face region (numpy array)

        Returns:
            Dictionary containing:
            {
                "status": "AUTHORIZED" | "UNCERTAIN" | "UNKNOWN" | "NO_REGISTERED_USERS" | "NO_FACES",
                "name": str or None,
                "distance": float,
                "confidence": float
            }
        """
        if face_crop is None or face_crop.size == 0:
            return {
                "status": "NO_FACES",
                "name": None,
                "distance": 1.0,
                "confidence": 0.0
            }

        if not self.authorized_database:
            return {
                "status": "NO_REGISTERED_USERS",
                "name": None,
                "distance": 1.0,
                "confidence": 0.0
            }

        query_emb = self._extract_embedding_from_crop(face_crop)
        if query_emb is None:
            return {
                "status": "UNKNOWN",
                "name": "Unknown Viewer",
                "distance": 1.0,
                "confidence": 0.0
            }

        best_name = None
        min_distance = float("inf")

        # Compare against enrolled identities (comparing with both mean and individual samples)
        for auth_name, data in self.authorized_database.items():
            candidate_embs = data.get("embeddings", [])
            mean_emb = data.get("mean_embedding")
            
            all_embs = list(candidate_embs)
            if mean_emb is not None and not any(np.array_equal(mean_emb, e) for e in all_embs):
                all_embs.append(mean_emb)

            for auth_emb in all_embs:
                if len(query_emb) != len(auth_emb):
                    continue
                
                # Cosine distance: 1 - (u . v) / (||u|| * ||v||)
                dot_val = float(np.dot(query_emb, auth_emb))
                norm_q = float(np.linalg.norm(query_emb))
                norm_a = float(np.linalg.norm(auth_emb))
                
                if norm_q > 0 and norm_a > 0:
                    cos_dist = max(0.0, 1.0 - (dot_val / (norm_q * norm_a)))
                else:
                    cos_dist = 1.0

                if cos_dist < min_distance:
                    min_distance = cos_dist
                    best_name = auth_name

        # 3-Tier Classification Decision
        if best_name is not None and min_distance <= self.distance_threshold:
            # Confirmed Authorized Owner
            confidence = max(0.0, min(1.0, 1.0 - (min_distance / self.distance_threshold) * 0.3))
            result = {
                "status": "AUTHORIZED",
                "name": best_name,
                "distance": round(float(min_distance), 3),
                "confidence": round(float(confidence), 2)
            }
        elif best_name is not None and min_distance <= self.uncertain_threshold:
            # Uncertain / Ambiguous match (never falsely authorize!)
            uncertain_range = self.uncertain_threshold - self.distance_threshold
            ratio = (min_distance - self.distance_threshold) / (uncertain_range if uncertain_range > 0 else 1.0)
            conf = max(0.40, min(0.69, 0.69 - ratio * 0.25))
            result = {
                "status": "UNCERTAIN",
                "name": f"Uncertain ({best_name}?)",
                "distance": round(float(min_distance), 3),
                "confidence": round(float(conf), 2)
            }
        else:
            # Confirmed Unknown Person
            conf = round(float(max(0.0, min(1.0, 1.0 - min_distance))), 2)
            result = {
                "status": "UNKNOWN",
                "name": "Unknown Viewer",
                "distance": round(float(min_distance if best_name else 1.0), 3),
                "confidence": conf
            }

        self._last_result = result
        return result

    def process_frame_detections(
        self,
        frame: np.ndarray,
        faces: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Process a list of detected faces, utilizing frame throttling/caching for high FPS.
        
        Args:
            frame: Full BGR frame
            faces: Output list of face dicts from FaceDetector
            
        Returns:
            List of faces enriched with recognition results
        """
        self._frame_counter += 1
        interval = config.recognition.recognition_interval_frames
        
        enriched_faces = []
        for i, face in enumerate(faces):
            bbox = face["bbox"]
            
            # Run recognition on interval or first frame
            if self._frame_counter % interval == 0 or "identity" not in face:
                from app.ai.face_detection import FaceDetector
                crop = FaceDetector.extract_face_crop(frame, bbox)
                identity = self.recognize_face(crop)
            else:
                identity = self._last_result

            enriched_face = dict(face)
            enriched_face["identity"] = identity
            enriched_faces.append(enriched_face)

        return enriched_faces

