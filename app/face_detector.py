# app/face_detector.py
import cv2
import numpy as np
import os

# Load Haar cascade
haar = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

def detect_faces_bboxes(img):
    """
    Returns list of boxes [(x1,y1,x2,y2), ...] and the original BGR image
    """
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = haar.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        boxes = []
        for (x, y, w, h) in faces:
            boxes.append((int(x), int(y), int(x+w), int(y+h)))
        return boxes, img
    except Exception as e:
        print(f"Face detection failed: {e}")
        return [], img

def read_image_bgr(path_or_bytes):
    """Read image from bytes or file path"""
    if isinstance(path_or_bytes, (bytes, bytearray)):
        try:
            arr = np.frombuffer(path_or_bytes, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            print(f"Failed to decode image bytes: {e}")
            return None
    else:
        try:
            return cv2.imread(path_or_bytes)
        except Exception as e:
            print(f"Failed to read image file: {e}")
            return None

def extract_face(image_path, size=(160,160)):
    """Extract face from image path"""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Could not read image")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = haar.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    if len(faces) == 0:
        raise ValueError("No face detected")
    x, y, w, h = faces[0]
    face = img[y:y+h, x:x+w]
    face = cv2.resize(face, size)
    face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
    return face
