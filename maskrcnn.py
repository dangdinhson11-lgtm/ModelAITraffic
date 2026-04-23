import cv2
import os
import argparse
import supervision as sv
from inference_sdk import InferenceHTTPClient
import torch
import torchvision
from torchvision.models.detection import (
    maskrcnn_resnet50_fpn,
    MaskRCNN_ResNet50_FPN_Weights,
)
from dotenv import load_dotenv
from tqdm import tqdm
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import gc

# 1. Load config
load_dotenv()
API_KEY = os.getenv("ROBOFLOW_API_KEY")
CLIENT = InferenceHTTPClient(api_url="https://serverless.roboflow.com", api_key=API_KEY)

# 2. Khoi tao Mask R-CNN (Toi uu RAM)
weights = MaskRCNN_ResNet50_FPN_Weights.DEFAULT
mask_model = maskrcnn_resnet50_fpn(weights=weights, progress=False).eval()
for param in mask_model.parameters():
    param.requires_grad = False


def process_video(source_path, output_path, model_id="annonate_datatftphcm/1"):
    video_info = sv.VideoInfo.from_video_path(source_path)
    tracker = sv.ByteTrack()

    # Nâng lên 320p để hình ảnh rõ hơn một chút
    TARGET_WIDTH = 320
    scale = TARGET_WIDTH / video_info.width
    target_height = int(video_info.height * scale)

    # Đảm bảo FPS không bị sai lệch (mặc định 25 nếu không đọc được)
    video_fps = video_info.fps if video_info.fps > 0 else 25
    new_video_info = sv.VideoInfo(
        width=TARGET_WIDTH,
        height=target_height,
        fps=video_fps,
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

    last_detections = sv.Detections.empty()
    stride = 5  # GIẢM STRIDE XUỐNG 5: Video sẽ mượt hơn gấp 3-4 lần bản trước
    unique_ids = set()
    analytics_data = []

    mask_annotator = sv.MaskAnnotator()
    zone_annotator = sv.PolygonZoneAnnotator(
        zone=zone, color=sv.Color.GREEN, thickness=1
    )

    def callback(frame: np.ndarray, index: int) -> np.ndarray:
        nonlocal last_detections
        frame_resized = cv2.resize(frame, (TARGET_WIDTH, target_height))

        if index % stride == 0:
            temp_img = "t_m.jpg"
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

            if preds:
                img_t = (
                    torch.from_numpy(frame_resized).permute(2, 0, 1).float().div(255)
                )
                with torch.inference_mode():
                    outputs = mask_model([img_t])[0]

                m_idx = np.where(outputs["scores"].cpu().numpy() > 0.4)[
                    0
                ]  # Giảm ngưỡng conf để bắt xe tốt hơn
                if len(m_idx) > 0:
                    masks = (outputs["masks"][m_idx] > 0.5).cpu().numpy().squeeze(1)
                    boxes = outputs["boxes"][m_idx].cpu().numpy()
                    detections = sv.Detections(
                        xyxy=boxes,
                        class_id=outputs["labels"][m_idx].cpu().numpy(),
                        confidence=outputs["scores"][m_idx].cpu().numpy(),
                        mask=masks,
                    )
                    detections = detections[np.isin(detections.class_id, [3, 4, 6, 8])]
                    last_detections = tracker.update_with_detections(
                        detections=detections
                    )
                else:
                    last_detections = sv.Detections.empty()
            else:
                last_detections = sv.Detections.empty()

        mask_area = 0
        if not last_detections.is_empty():
            if last_detections.mask is not None:
                mask_area = np.sum(last_detections.mask)
            if last_detections.tracker_id is not None:
                for tid in last_detections.tracker_id:
                    unique_ids.add(tid)

        occ = min((mask_area / road_area_pixels) * 100, 100.0)

        # Lưu dữ liệu mỗi giây
        if index % int(video_fps) == 0:
            analytics_data.append({"time": index // video_fps, "density": occ})

        annotated_frame = mask_annotator.annotate(
            scene=frame_resized.copy(), detections=last_detections
        )
        annotated_frame = zone_annotator.annotate(scene=annotated_frame)
        cv2.putText(
            annotated_frame,
            f"Density: {occ:.1f}% | Total: {len(unique_ids)}",
            (10, 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (255, 255, 0),
            1,
        )
        return annotated_frame

    generator = sv.get_video_frames_generator(source_path=source_path)
    # Ghi lại từng khung hình để video không bị ngắn lại
    with sv.VideoSink(
        target_path=output_path, video_info=new_video_info, codec="MJPG"
    ) as sink:
        for index, frame in enumerate(
            tqdm(
                generator, total=video_info.total_frames, desc="Smooth Mask Processing"
            )
        ):
            processed_frame = callback(frame, index)
            sink.write_frame(frame=processed_frame)
            if index % 10 == 0:
                gc.collect()

    # Vẽ biểu đồ nâng cao
    df = pd.DataFrame(analytics_data)
    if not df.empty:
        plt.figure(figsize=(12, 6))
        # Phân loại mức độ bằng màu nền
        plt.axhspan(0, 25, color="green", alpha=0.1, label="Thong thoang")
        plt.axhspan(25, 60, color="yellow", alpha=0.1, label="Trung binh")
        plt.axhspan(60, 100, color="red", alpha=0.1, label="Tac nghen")

        plt.plot(
            df["time"],
            df["density"],
            color="blue",
            linewidth=2,
            marker="o",
            label="Mat do thuc te (Pixel %)",
        )
        plt.title("Phan tich Mat do Giao thong bang mat na Pixel (Mask R-CNN)")
        plt.xlabel("Thoi gian (Giay)")
        plt.ylabel("Dien tich Chiem dung (%)")
        plt.ylim(0, 100)
        plt.legend()
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.savefig("mask_traffic_chart.png")
        print(f"\n--- SUCCESS! Chart saved: mask_traffic_chart.png ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str)
    parser.add_argument("--output", type=str, default="output_mask_smooth.avi")
    args = parser.parse_args()
    input_p = args.input if args.input else input("File: ")
    if os.path.exists(input_p):
        process_video(
            input_p,
            args.output if args.output.endswith(".avi") else args.output + ".avi",
        )
