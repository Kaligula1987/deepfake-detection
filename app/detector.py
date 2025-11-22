# app/detector.py
import os
import io
from PIL import Image
import numpy as np
import cv2

try:
    from .utils import compute_ela_score, variance_of_laplacian_cv2, image_entropy, extract_exif
    from .face_detector import detect_faces_bboxes, read_image_bgr
except ImportError:
    from utils import compute_ela_score, variance_of_laplacian_cv2, image_entropy, extract_exif
    from face_detector import detect_faces_bboxes, read_image_bgr

def predict_deepfake_on_face(face_bgr):
    """Predict if a face is deepfake"""
    # Placeholder for your model - returns None for now
    return None

def ai_generated_score(pil_img):
    """Heuristic AI-generated image detection"""
    try:
        ela_mean, ela_std = compute_ela_score(pil_img, quality=90)
        ent = image_entropy(pil_img)
        arr = np.array(pil_img.convert("RGB"))[:,:,::-1]  # BGR
        lap_var = variance_of_laplacian_cv2(arr)

        # AI images often have lower ELA, lower entropy, and are overly sharp
        ela_score = min(1.0, (0.08 - ela_mean) / 0.08) if ela_mean < 0.08 else 0.0
        sharp_score = min(1.0, max(0.0, (100.0 - lap_var) / 100.0))
        ent_score = min(1.0, max(0.0, (6.0 - ent) / 6.0))

        agg = (ela_score * 0.5) + (sharp_score * 0.3) + (ent_score * 0.2)
        return float(max(0.0, min(1.0, agg)))
    except Exception as e:
        print(f"AI-generated scoring failed: {e}")
        return 0.0

def manipulation_score(pil_img):
    """Heuristic image manipulation detection"""
    try:
        ela_mean, ela_std = compute_ela_score(pil_img, quality=90)
        exif = extract_exif(pil_img)
        has_exif = 1 if exif else 0

        # Higher ELA means more compression artifacts = more likely manipulated
        ela_feature = min(1.0, ela_mean / 0.15)
        exif_score = 0.0 if has_exif else 0.2  # No EXIF = more suspicious

        score = min(1.0, ela_feature + exif_score)
        return float(score)
    except Exception as e:
        print(f"Manipulation scoring failed: {e}")
        return 0.0

def analyze_image_bytes(image_bytes):
    """Main analysis function"""
    try:
        # Read image
        bgr = read_image_bgr(image_bytes)
        if bgr is None:
            return {"error": "Cannot open image"}

        # PIL image for other analyses
        pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # Detect faces and analyze each one
        boxes, _ = detect_faces_bboxes(bgr)
        faces_results = []
        
        for i, (x1, y1, x2, y2) in enumerate(boxes):
            face = bgr[y1:y2, x1:x2]
            df_score = predict_deepfake_on_face(face)
            faces_results.append({
                "face_id": i,
                "box": [int(x1), int(y1), int(x2), int(y2)],
                "deepfake_score": df_score
            })

        # Image-wide scores
        ai_score = ai_generated_score(pil)
        manip_score = manipulation_score(pil)

        # Final decision
        deepfake_face_scores = [f["deepfake_score"] for f in faces_results if f["deepfake_score"] is not None]
        
        # Calculate confidence
        confidence_scores = []
        if deepfake_face_scores:
            confidence_scores.append(max(deepfake_face_scores))
        confidence_scores.append(ai_score)
        confidence_scores.append(manip_score)
        
        overall_confidence = max(confidence_scores) if confidence_scores else 0.0

        # Determine final label
        if deepfake_face_scores and max(deepfake_face_scores) > 0.6:
            final_label = "Deepfake"
            confidence = max(deepfake_face_scores)
        elif ai_score > 0.6:
            final_label = "AI-generated"
            confidence = ai_score
        elif manip_score > 0.5:
            final_label = "Manipulated/Edited"
            confidence = manip_score
        else:
            final_label = "Likely Real"
            confidence = 1.0 - overall_confidence

        result = {
            "faces": faces_results,
            "ai_score": round(ai_score, 3),
            "manipulation_score": round(manip_score, 3),
            "final_label": final_label,
            "confidence": round(confidence, 3),
            "faces_detected": len(faces_results),
            "analysis_complete": True
        }

        return result

    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}"}
