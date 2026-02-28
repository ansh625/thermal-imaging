import cv2

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Camera NOT opening ❌")
else:
    print("Camera working ✅")

cap.release()