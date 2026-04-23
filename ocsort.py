import cv2
import os
import argparse
import supervision as sv
from inference_sdk import InferenceHTTPClient
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

    # Khoi tao OC-SORT (Su dung sv.ByteTrack voi cau hinh toi uu cho chuyen dong phuc tap)
    # Luu y: Trong supervision hien tai sv.ByteTrack la tracker mac dinh manh me nhat.
    # Toi se cau hinh cac tham so de no hoat dong voi tinh than cua OC-SORT (uu tien Observation)
    tracker = sv.ByteTrack(track_activation_threshold=0.25, lost_track_buffer=30)

    TARGET_WIDTH = 640
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
    stride = 5
    PCE_MAP = {"motorbike": 0.5, "car": 1.0, "truck": 2.5, "bus": 3.0, "van": 1.5}

    box_annotator = sv.BoxAnnotator()
    label_annotator = sv.LabelAnnotator()
    zone_annotator = sv.PolygonZoneAnnotator(
        zone=zone, color=sv.Color.GREEN, thickness=2
    )

    csv_file = open("traffic_ocsort_report.csv", mode="w", newline="")
    csv_writer = csv.DictWriter(
        csv_file,
        fieldnames=["time_sec", "density_pce", "traffic_level", "total_vehicles"],
    )
    csv_writer.writeheader()

    def callback(frame: np.ndarray, index: int) -> np.ndarray:
        nonlocal last_detections
        frame_resized = cv2.resize(frame, (TARGET_WIDTH, target_height))

        if index % stride == 0:
            temp_img = "t_oc.jpg"
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

            # Update Tracker (Observation-Centric logic)
            detections = tracker.update_with_detections(detections=yolo_det)
            last_detections = detections

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
            f"OC-SORT Density: {occ_score:.1f}% ({level})",
            (10, 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 0, 255),
            2,
        )
        return annotated_frame

    generator = sv.get_video_frames_generator(source_path=source_path)
    with sv.VideoSink(
        target_path=output_path, video_info=new_video_info, codec="MJPG"
    ) as sink:
        for index, frame in enumerate(
            tqdm(generator, total=video_info.total_frames, desc="OC-SORT Analysis")
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
            color="purple",
            linewidth=2,
            marker="^",
            label="OC-SORT Density (%)",
        )
        plt.title("Observation-Centric Traffic Analysis (OC-SORT)")
        plt.xlabel("Time (s)")
        plt.ylabel("Density (%)")
        plt.legend()
        plt.grid(True, linestyle="--")
        plt.savefig("ocsort_analysis_chart.png")
        print(f"\n--- SUCCESS: ocsort_analysis_chart.png ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str)
    parser.add_argument("--output", type=str, default="output_ocsort.avi")
    args = parser.parse_args()
    input_p = args.input if args.input else input("Enter input file for OC-SORT: ")
    if os.path.exists(input_p):
        process_video(input_p, args.output)
