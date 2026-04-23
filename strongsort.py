import cv2
import os
import argparse
import supervision as sv
from inference_sdk import InferenceHTTPClient
from deep_sort_realtime.deepsort_tracker import DeepSort
from dotenv import load_dotenv
from tqdm import tqdm
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import gc
import csv

# 1. Load config
load_dotenv()
API_KEY = os.getenv("ROBOFLOW_API_KEY")
CLIENT = InferenceHTTPClient(api_url="https://serverless.roboflow.com", api_key=API_KEY)


def get_traffic_level(occupancy):
    if occupancy < 30:
        return "Thong thoang"
    if occupancy < 70:
        return "Trung binh"
    return "Tac nghen"


def process_video(source_path, output_path, model_id="annonate_datatftphcm/1"):
    video_info = sv.VideoInfo.from_video_path(source_path)

    # Khoi tao StrongSORT (Dung DeepSort voi cau hinh nang cao de mo phong StrongSORT)
    # Su dung Mobilenet de lay appearance features, giup theo doi ben vung
    tracker = DeepSort(
        max_age=30,  # Nho doi tuong trong 30 khung hinh (Stronger than standard)
        nn_budget=100,  # Luu tru nhieu dac trung hon de nhan dien lai xe
        embedder="mobilenet",
        embedder_gpu=False,  # Chay CPU de tiet kiem RAM
        max_iou_distance=0.7,
    )

    # Nen xuong 480p de can bang giua RAM va Do chinh xac cua StrongSORT
    TARGET_WIDTH = 480
    scale = TARGET_WIDTH / video_info.width
    target_height = int(video_info.height * scale)
    new_video_info = sv.VideoInfo(
        width=TARGET_WIDTH,
        height=target_height,
        fps=video_info.fps,
        total_frames=video_info.total_frames,
    )

    polygon = np.array(
        [
            [0, target_height],
            [int(TARGET_WIDTH * 0.1), int(target_height * 0.3)],
            [int(TARGET_WIDTH * 0.9), int(target_height * 0.3)],
            [TARGET_WIDTH, target_height],
        ]
    )
    road_area_pixels = cv2.contourArea(polygon.astype(np.int32))
    zone = sv.PolygonZone(polygon=polygon)

    analytics_data = []
    unique_ids_seen = set()
    last_detections = sv.Detections.empty()
    stride = 10  # Nhay 10 khung hinh
    PCE_MAP = {"motorbike": 0.5, "car": 1.0, "truck": 2.5, "bus": 3.0, "van": 1.5}

    box_annotator = sv.BoxAnnotator()
    label_annotator = sv.LabelAnnotator()
    zone_annotator = sv.PolygonZoneAnnotator(
        zone=zone, color=sv.Color.GREEN, thickness=2
    )

    csv_file = open("traffic_strongsort_report.csv", mode="w", newline="")
    csv_writer = csv.DictWriter(
        csv_file,
        fieldnames=["time_sec", "density_pce", "traffic_level", "total_vehicles"],
    )
    csv_writer.writeheader()

    def callback(frame: np.ndarray, index: int) -> np.ndarray:
        nonlocal last_detections
        frame_resized = cv2.resize(frame, (TARGET_WIDTH, target_height))

        if index % stride == 0:
            temp_img = "t_s.jpg"
            cv2.imwrite(temp_img, frame_resized)
            result = CLIENT.infer(temp_img, model_id=model_id)

            preds = result.get("predictions", [])
            if isinstance(preds, dict):
                all_p = []
                for k, v in preds.items():
                    for p in v:
                        p["class"] = k
                        all_p.append(p)
                preds = all_p

            yolo_det = sv.Detections.from_inference(
                {
                    "predictions": preds,
                    "image": {"width": TARGET_WIDTH, "height": target_height},
                }
            )

            # Chuyen sang format StrongSORT (Appearance-based)
            ds_detections = []
            if "class_name" in yolo_det.data:
                for xyxy, conf, cls in zip(
                    yolo_det.xyxy, yolo_det.confidence, yolo_det.data["class_name"]
                ):
                    x1, y1, x2, y2 = xyxy
                    ds_detections.append(([x1, y1, x2 - x1, y2 - y1], conf, cls))

            # Update Tracker (StrongSORT logic)
            tracks = tracker.update_tracks(ds_detections, frame=frame_resized)
            tx, ti, tc = [], [], []
            for t in tracks:
                if not t.is_confirmed():
                    continue
                tx.append(t.to_ltrb())
                ti.append(t.track_id)
                tc.append(t.get_det_class())

            last_detections = (
                sv.Detections(
                    xyxy=np.array(tx),
                    tracker_id=np.array(ti),
                    class_id=np.array([0] * len(ti)),
                    data={"class_name": np.array(tc)},
                )
                if tx
                else sv.Detections.empty()
            )

        detections = last_detections
        mask = zone.trigger(detections=detections)
        det_in_zone = detections[mask]

        curr_pce = 0
        if det_in_zone.tracker_id is not None and "class_name" in det_in_zone.data:
            for cls, tid in zip(det_in_zone.data["class_name"], det_in_zone.tracker_id):
                curr_pce += PCE_MAP.get(cls, 1.0)
                unique_ids_seen.add(tid)

        occ_score = min((curr_pce * 15000 / road_area_pixels) * 100, 100.0)
        level = get_traffic_level(occ_score)

        fps = int(video_info.fps) if video_info.fps > 0 else 30
        if index % fps == 0:
            csv_writer.writerow(
                {
                    "time_sec": index // fps,
                    "density_pce": f"{occ_score:.1f}",
                    "traffic_level": level,
                    "total_vehicles": len(unique_ids_seen),
                }
            )
            csv_file.flush()
            analytics_data.append({"time": index // fps, "density": occ_score})

        # Visualize
        annotated_frame = box_annotator.annotate(
            scene=frame_resized.copy(), detections=detections
        )
        labels = (
            [
                f"ID:{tid} {cls}"
                for tid, cls in zip(
                    detections.tracker_id, detections.data["class_name"]
                )
            ]
            if not detections.is_empty() and "class_name" in detections.data
            else []
        )
        annotated_frame = label_annotator.annotate(
            scene=annotated_frame, detections=detections, labels=labels
        )
        annotated_frame = zone_annotator.annotate(scene=annotated_frame)

        cv2.putText(
            annotated_frame,
            f"StrongSORT Density: {occ_score:.1f}% ({level})",
            (10, 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 255, 255),
            2,
        )
        return annotated_frame

    generator = sv.get_video_frames_generator(source_path=source_path)
    with sv.VideoSink(
        target_path=output_path, video_info=new_video_info, codec="MJPG"
    ) as sink:
        for index, frame in enumerate(
            tqdm(generator, total=video_info.total_frames, desc="StrongSORT Analysis")
        ):
            sink.write_frame(frame=callback(frame, index))
            if index % 10 == 0:
                gc.collect()

    csv_file.close()

    # Save Chart
    df = pd.DataFrame(analytics_data)
    if not df.empty:
        plt.figure(figsize=(12, 6))
        plt.axhspan(0, 30, color="green", alpha=0.1, label="Clear")
        plt.axhspan(30, 70, color="yellow", alpha=0.1, label="Moderate")
        plt.axhspan(70, 100, color="red", alpha=0.1, label="Congested")
        plt.plot(
            df["time"],
            df["density"],
            color="orange",
            linewidth=2,
            marker="s",
            label="StrongSORT Density (%)",
        )
        plt.title("Advanced Traffic Analysis (StrongSORT + Appearance Features)")
        plt.xlabel("Time (s)")
        plt.ylabel("Density (%)")
        plt.legend()
        plt.grid(True, linestyle="--")
        plt.savefig("strongsort_analysis_chart.png")
        print(f"\n--- SUCCESS: strongsort_analysis_chart.png ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str)
    parser.add_argument("--output", type=str, default="output_strongsort.avi")
    args = parser.parse_args()
    input_p = args.input if args.input else input("Enter input file for StrongSORT: ")
    if os.path.exists(input_p):
        process_video(input_p, args.output)
