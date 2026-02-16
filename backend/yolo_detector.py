from ultralytics import YOLO
import cv2
import numpy as np
from typing import List, Dict, Tuple
import logging
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YOLODetector:
    def __init__(self, model_path: str = 'yolov8n.pt'):
        self.model = None
        self.model_path = model_path
        self.is_loaded = False
        
        # Target classes for detection (COCO dataset)
        self.target_classes = {
            0: 'person',
            1: 'bicycle',
            2: 'car',
            3: 'motorcycle',
            5: 'bus',
            7: 'truck',
            14: 'bird',
            15: 'cat',
            16: 'dog',
        }
        
        self.load_model()
    
    def load_model(self):
        """Load YOLO model"""
        try:
            self.model = YOLO(self.model_path)
            self.is_loaded = True
            logger.info(f"YOLO model loaded: {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            self.is_loaded = False
    
    def detect(self, frame: np.ndarray, confidence: float = 0.5) -> List[Dict]:
        """
        Perform object detection on frame
        Returns list of detections with bounding boxes
        """
        if not self.is_loaded:
            return []
        
        try:
            results = self.model(frame, conf=confidence, verbose=False)
            detections = []
            
            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue
                
                for box in boxes:
                    class_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = map(float, box.xyxy[0].cpu().numpy())
                    
                    # Only include target classes
                    if class_id in self.target_classes:
                        detections.append({
                            'class_id': class_id,
                            'class_name': self.target_classes[class_id],
                            'confidence': conf,
                            'bbox': {
                                'x1': int(x1),
                                'y1': int(y1),
                                'x2': int(x2),
                                'y2': int(y2)
                            }
                        })
            
            return detections
            
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return []
    
    def draw_detections(self, frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """Draw bounding boxes on frame"""
        frame_copy = frame.copy()
        
        for det in detections:
            bbox = det['bbox']
            x1, y1, x2, y2 = bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2']
            
            # Draw rectangle
            cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw label
            label = f"{det['class_name']} {det['confidence']:.2f}"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame_copy, (x1, y1 - h - 10), (x1 + w, y1), (0, 255, 0), -1)
            cv2.putText(frame_copy, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
        return frame_copy
    
    def save_detection(self, frame: np.ndarray, detection: Dict, 
                      output_dir: str = "detections") -> str:
        """Save detected object as image"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        class_name = detection['class_name']
        filename = f"{class_name}_{timestamp}.jpg"
        filepath = os.path.join(output_dir, filename)
        
        # Crop detected region
        bbox = detection['bbox']
        x1, y1, x2, y2 = bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2']
        
        # Add padding
        padding = 20
        h, w = frame.shape[:2]
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(w, x2 + padding)
        y2 = min(h, y2 + padding)
        
        cropped = frame[y1:y2, x1:x2]
        cv2.imwrite(filepath, cropped)
        
        return filepath

# Global instance
yolo_detector = YOLODetector()