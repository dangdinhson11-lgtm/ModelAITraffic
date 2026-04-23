import cv2
import os
import argparse
import supervision as sv
from inference_sdk import InferenceHTTPClient
from deep_sort_realtime.deepsort_tracker import DeepSort
import torch
import torchvision
from torchvision.models.detection import maskrcnn_resnet50_fpn, MaskRCNN_ResNet50_FPN_Weights
from dotenv import load_dotenv
from tqdm import tqdm
import numpy as np
import pandas as pd
import gc
import csv

# 1. Load config
load_dotenv()
API_KEY = os.getenv("ROBOFLOW_API_KEY")
CLIENT = InferenceHTTPClient(api_url="https://serverless.roboflow.com", api_key=API_KEY)

# Hệ số PCE và Diện tích chuẩn (Theo yolo_deepsort_logic.md)
PCE_MAP = {"motorbike": 0.5, "car": 1.0, "truck": 2.5, "bus": 3.0, "van": 1.5}
STANDARD_CAR_AREA = 1200

def process_video(source_path, output_path, mode="fast", report_path="traffic_report.csv", progress_path=None, model_id="annonate_datatftphcm/1"):
    video_info = sv.VideoInfo.from_video_path(source_path)
    
    # 2. Pipeline Initialization
    if mode == "mask":
        TARGET_WIDTH = 320; stride = 15
        mask_model = maskrcnn_resnet50_fpn(weights=MaskRCNN_ResNet50_FPN_Weights.DEFAULT, progress=False).eval()
        for param in mask_model.parameters(): param.requires_grad = False
        tracker = sv.ByteTrack()
    else:
        TARGET_WIDTH = 640; stride = 5
        if mode == "fast": tracker = sv.ByteTrack()
        elif mode == "motion": tracker = sv.ByteTrack(track_activation_threshold=0.25, lost_track_buffer=30)
        elif mode == "stable": 
            # DeepSort Tracker với Appearance Embeddings
            tracker = DeepSort(max_age=30, nn_budget=50, embedder="mobilenet", embedder_gpu=False)

    scale = TARGET_WIDTH / video_info.width
    target_height = int(video_info.height * scale)
    new_video_info = sv.VideoInfo(width=TARGET_WIDTH, height=target_height, fps=video_info.fps, total_frames=video_info.total_frames)
    
    # Vùng ROI (Polygon)
    polygon = np.array([[0, target_height], [int(TARGET_WIDTH*0.1), int(target_height*0.3)], [int(TARGET_WIDTH*0.9), int(target_height*0.3)], [TARGET_WIDTH, target_height]])
    road_area = cv2.contourArea(polygon.astype(np.int32))
    zone = sv.PolygonZone(polygon=polygon)
    
    unique_ids = set()
    last_det = sv.Detections.empty()
    csv_file = open(report_path, mode="w", newline="")
    csv_writer = csv.DictWriter(csv_file, fieldnames=["time_sec", "density_pce", "total_vehicles"])
    csv_writer.writeheader()

    def callback(frame, index):
        nonlocal last_det
        fr = cv2.resize(frame, (TARGET_WIDTH, target_height))
        if index % stride == 0:
            temp = f"t_{os.getpid()}.jpg"
            cv2.imwrite(temp, fr)
            # Goi API khong truyen confidence neu bi loi
            res = CLIENT.infer(temp, model_id=model_id)
            os.remove(temp)

            all_raw_preds = res.get('predictions', [])
            if isinstance(all_raw_preds, dict):
                all_p = []
                for k, v in all_raw_preds.items():
                    for p in v: p['class'] = k; all_p.append(p)
                all_raw_preds = all_p

            # LOC THU CONG VOI NGUONG 0.2
            preds = [p for p in all_raw_preds if p.get('confidence', 0) >= 0.2]

            yolo_det = sv.Detections.from_inference({"predictions": preds, "image": {"width": TARGET_WIDTH, "height": target_height}})

            
            # --- Logic DeepSort Integration ---
            if mode == "stable":
                ds_det = []
                if 'class_name' in yolo_det.data:
                    for xyxy, conf, cls in zip(yolo_det.xyxy, yolo_det.confidence, yolo_det.data['class_name']):
                        ds_det.append(([xyxy[0], xyxy[1], xyxy[2]-xyxy[0], xyxy[3]-xyxy[1]], conf, cls))
                tracks = tracker.update_tracks(ds_det, frame=fr)
                tx, ti, tc = [], [], []
                for t in tracks:
                    if t.is_confirmed(): tx.append(t.to_ltrb()); ti.append(t.track_id); tc.append(t.get_det_class())
                last_det = sv.Detections(xyxy=np.array(tx), tracker_id=np.array(ti), class_id=np.array([0]*len(ti)), data={'class_name': np.array(tc)}) if tx else sv.Detections.empty()
            elif mode == "mask":
                img_t = torch.from_numpy(fr).permute(2, 0, 1).float().div(255)
                with torch.inference_mode(): outputs = mask_model([img_t])[0]
                m_idx = np.where(outputs['scores'].cpu().numpy() > 0.5)[0]
                if len(m_idx) > 0:
                    det = sv.Detections(xyxy=outputs['boxes'][m_idx].cpu().numpy(), class_id=outputs['labels'][m_idx].cpu().numpy(), confidence=outputs['scores'][m_idx].cpu().numpy(), mask=(outputs['masks'][m_idx] > 0.5).cpu().numpy().squeeze(1))
                    det = det[np.isin(det.class_id, [3, 4, 6, 8])]
                    last_det = tracker.update_with_detections(detections=det)
                else: last_det = sv.Detections.empty()
            else:
                last_det = tracker.update_with_detections(detections=yolo_det)

        # --- Logic Analytics (Tuân thủ yolo_deepsort_logic.md) ---
        mask = zone.trigger(detections=last_det)
        det_in = last_det[mask]
        pce_sum_area = 0
        if not det_in.is_empty():
            if 'class_name' in det_in.data:
                for cls, tid in zip(det_in.data['class_name'], det_in.tracker_id):
                    # Công thức: D = Sum(w_i * Standard_Area)
                    pce_sum_area += (PCE_MAP.get(cls, 1.0) * STANDARD_CAR_AREA)
                    unique_ids.add(tid)
            elif det_in.tracker_id is not None:
                pce_sum_area += (len(det_in.tracker_id) * STANDARD_CAR_AREA)
                for tid in det_in.tracker_id: unique_ids.add(tid)

        # Mật độ (%) = (Diện tích xe quy đổi / Diện tích lòng đường) * 100
        occ = min((pce_sum_area / road_area) * 100, 100.0)
        
        if index % int(video_info.fps or 30) == 0:
            csv_writer.writerow({"time_sec": index // int(video_info.fps or 30), "density_pce": round(occ, 1), "total_vehicles": len(unique_ids)})
            csv_file.flush()
        
        if progress_path and index % 10 == 0:
            with open(progress_path, 'w') as f: f.write(str(int((index / video_info.total_frames) * 100)))

        annotated = sv.BoxAnnotator().annotate(scene=fr.copy(), detections=last_det)
        annotated = sv.PolygonZoneAnnotator(zone=zone, color=sv.Color.GREEN, thickness=1).annotate(scene=annotated)
        cv2.putText(annotated, f"{mode.upper()} | D: {occ:.1f}% | Count: {len(unique_ids)}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        return annotated

    generator = sv.get_video_frames_generator(source_path=source_path)
    codec = "VP80" if output_path.endswith('.webm') else "mp4v"
    with sv.VideoSink(target_path=output_path, video_info=new_video_info, codec=codec) as sink:
        for index, frame in enumerate(tqdm(generator, total=video_info.total_frames, desc=f"AI Running")):
            sink.write_frame(frame=callback(frame, index))
            if index % 20 == 0: gc.collect() 
    csv_file.close()
    if progress_path: 
        with open(progress_path, 'w') as f: f.write("100")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str)
    parser.add_argument('--mode', type=str, default='fast')
    parser.add_argument('--output', type=str, default='result.webm')
    parser.add_argument('--report', type=str, default='traffic_report.csv')
    parser.add_argument('--progress', type=str, default=None)
    args = parser.parse_args()
    process_video(args.input, args.output, mode=args.mode, report_path=args.report, progress_path=args.progress)
