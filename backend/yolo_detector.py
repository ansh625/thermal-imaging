# 🔐 PyTorch 2.6+ SAFE YOLO LOADING (COMPLETE FIX)
import torch
from ultralytics.nn.tasks import DetectionModel
from torch.nn.modules.container import Sequential

# Allow required YOLO globals
torch.serialization.add_safe_globals([
    DetectionModel,
    Sequential
])

# --------------------------------------------------

from ultralytics import YOLO
import cv2
import numpy as np
from typing import List, Dict
import logging
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YOLODetector:
    def __init__(self, model_path: str = "yolov8n.pt"):
        self.model = None
        self.model_path = model_path
        self.is_loaded = False

        # Target classes (COCO)
        self.target_classes = {
            0: "person",
            1: "bicycle",
            2: "car",
            3: "motorcycle",
            5: "bus",
            7: "truck",
            14: "bird",
            15: "cat",
            16: "dog",
        }

        self.load_model()

    def load_model(self):
        """Load YOLO model with optimizations"""
        try:
            self.model = YOLO(self.model_path)
            # Use GPU if available for faster inference
            if torch.cuda.is_available():
                self.model.to('cuda')
                logger.info("Using CUDA GPU for detection")
            self.is_loaded = True
            logger.info(f"✅ YOLO model loaded successfully: {self.model_path}")
        except Exception as e:
            logger.error(f"❌ Failed to load YOLO model: {e}")
            self.is_loaded = False

    def detect(self, frame: np.ndarray, confidence: float = 0.5) -> List[Dict]:
        """Fast detection with minimal overhead"""
        if not self.is_loaded:
            return []

        try:
            # Use smaller inference size for speed
            results = self.model(
                frame, 
                conf=confidence, 
                verbose=False,
                imgsz=384  # Smaller = faster, balanced accuracy
            )
            detections = []

            for result in results:
                if result.boxes is None:
                    continue

                for box in result.boxes:
                    class_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = map(float, box.xyxy[0].cpu().numpy())

                    if class_id in self.target_classes:
                        detections.append({
                            "class_id": class_id,
                            "class_name": self.target_classes[class_id],
                            "confidence": conf,
                            "bbox": {
                                "x1": int(x1),
                                "y1": int(y1),
                                "x2": int(x2),
                                "y2": int(y2),
                            },
                        })

            return detections

        except Exception as e:
            logger.error(f"Detection error: {e}")
            return []

    def draw_detections(self, frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
        frame_copy = frame.copy()

        for det in detections:
            b = det["bbox"]
            x1, y1, x2, y2 = b["x1"], b["y1"], b["x2"], b["y2"]

            cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)

            label = f"{det['class_name']} {det['confidence']:.2f}"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)

            cv2.rectangle(frame_copy, (x1, y1 - h - 10), (x1 + w, y1), (0, 255, 0), -1)
            cv2.putText(
                frame_copy,
                label,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 0),
                2,
            )

        return frame_copy

    def save_detection(self, frame: np.ndarray, detection: Dict, output_dir="detections") -> str:
        os.makedirs(output_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = detection["class_name"]
        path = os.path.join(output_dir, f"{name}_{ts}.jpg")

        b = detection["bbox"]
        pad = 20
        h, w = frame.shape[:2]

        x1 = max(0, b["x1"] - pad)
        y1 = max(0, b["y1"] - pad)
        x2 = min(w, b["x2"] + pad)
        y2 = min(h, b["y2"] + pad)

        crop = frame[y1:y2, x1:x2]
        cv2.imwrite(path, crop)

        return path

# ✅ Global instance
yolo_detector = YOLODetector()
