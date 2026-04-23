import os
import cv2
import numpy as np
from inference_sdk import InferenceHTTPClient
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("ROBOFLOW_API_KEY")
CLIENT = InferenceHTTPClient(api_url="https://serverless.roboflow.com", api_key=API_KEY)

# 1. He so quy doi PCE
PCE_MAP = {"motorbike": 0.5, "car": 1.0, "truck": 2.5, "bus": 3.0, "van": 1.5}
STANDARD_CAR_AREA = 1200

def analyze_image(image_path, road_area_pixels=15000):
    """
    Phan tich anh. Su dung filter thu cong neu API khong cho phep truyen confidence.
    """
    result = CLIENT.infer(image_path, model_id="annonate_datatftphcm/1")
    
    predictions = result.get('predictions', [])
    if isinstance(predictions, dict):
        all_p = []
        for k, v in predictions.items():
            for p in v: p['class'] = k; all_p.append(p)
        predictions = all_p

    # LOC THU CONG VOI NGUONG 0.2 (20%)
    filtered_preds = [p for p in predictions if p.get('confidence', 0) >= 0.2]

    vehicle_count = len(filtered_preds)
    pce_sum_area = 0
    for p in filtered_preds:
        pce_weight = PCE_MAP.get(p.get('class', ''), 1.0)
        pce_sum_area += (pce_weight * STANDARD_CAR_AREA)

    density = min((pce_sum_area / road_area_pixels) * 100, 100.0) 
    
    traffic_level = "Thông thoáng"
    if density > 70: traffic_level = "Tắc nghẽn"
    elif density > 35: traffic_level = "Trung bình"

    return {
        "vehicle_count": vehicle_count,
        "density": round(density, 1),
        "traffic_level": traffic_level,
        "predictions": filtered_preds
    }
