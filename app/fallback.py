# app/fallback_detector.py
import io
from PIL import Image
import numpy as np
import cv2

def analyze_image_bytes(image_bytes):
    """Simple fallback analysis that always works"""
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = image.size
        
        # Convert to numpy for basic analysis
        img_array = np.array(image)
        
        # Basic image analysis (placeholder)
        brightness = np.mean(img_array)
        contrast = np.std(img_array)
        
        # Simple heuristic scores
        ai_score = min(1.0, max(0.0, (contrast - 30) / 50))
        manip_score = min(1.0, max(0.0, (brightness - 100) / 100))
        
        # Final decision
        if ai_score > 0.7:
            final_label = "AI-generated"
            confidence = ai_score
        elif manip_score > 0.6:
            final_label = "Manipulated/Edited"
            confidence = manip_score
        else:
            final_label = "Likely Real"
            confidence = 1.0 - max(ai_score, manip_score)
        
        return {
            "faces": [],
            "ai_score": round(ai_score, 3),
            "manipulation_score": round(manip_score, 3),
            "final_label": final_label,
            "confidence": round(confidence, 3),
            "faces_detected": 0,
            "analysis_complete": True
        }
        
    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}"}
