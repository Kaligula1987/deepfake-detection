# app/utils.py
from PIL import Image, ExifTags
import io
import numpy as np
import cv2
import math

def compute_ela_score(pil_img, quality=90):
    """
    Error Level Analysis: save at quality, compute difference.
    Returns mean and std of absolute diff normalized.
    """
    try:
        buf = io.BytesIO()
        pil_img.save(buf, 'JPEG', quality=quality)
        buf.seek(0)
        recompressed = Image.open(buf).convert('RGB')

        arr_orig = np.asarray(pil_img).astype(np.int16)
        arr_recomp = np.asarray(recompressed).astype(np.int16)
        diff = np.abs(arr_orig - arr_recomp).astype(np.uint8)
        
        # normalized score
        mean = float(diff.mean()) / 255.0
        std = float(diff.std()) / 255.0
        return mean, std
    except Exception as e:
        print(f"ELA computation failed: {e}")
        return 0.0, 0.0

def variance_of_laplacian_cv2(bgr_img):
    """Compute Laplacian variance for sharpness detection"""
    try:
        gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
    except Exception as e:
        print(f"Laplacian computation failed: {e}")
        return 0.0

def image_entropy(pil_img):
    """Calculate image entropy"""
    try:
        hist = pil_img.convert('L').histogram()
        hist_sum = sum(hist)
        if hist_sum == 0:
            return 0.0
            
        hist_norm = [h / hist_sum for h in hist if h > 0]
        ent = -sum([p * math.log2(p) for p in hist_norm if p > 0])
        return ent
    except Exception as e:
        print(f"Entropy computation failed: {e}")
        return 0.0

def extract_exif(pil_img):
    """Extract EXIF metadata from image"""
    try:
        exif = pil_img._getexif()
        if not exif:
            return {}
        nice = {}
        for k, v in exif.items():
            name = ExifTags.TAGS.get(k, k)
            nice[name] = v
        return nice
    except Exception:
        return {}
