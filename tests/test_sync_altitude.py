"""
测试完整处理流程中的pose数据
"""
import cv2
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.input.osd_ocr_reader import OSDOCRReader
from src.sync.data_synchronizer import DataSynchronizer

video_path = "data/input/videos/siluan0212.mp4"
cap = cv2.VideoCapture(video_path)

# 读取第一帧
ret, frame = cap.read()
if not ret:
    print("Cannot read frame")
    exit(1)

# 初始化OCR
ocr_reader = OSDOCRReader(
    roi_config={'x': 0, 'y': 0, 'width': 600, 'height': 300},
    cache_enabled=False,
    frame_interval=1,
    use_gpu=False
)

# 提取位姿
pose_from_ocr = ocr_reader.extract_pose_from_frame(frame, 0, 0.0)
print("\n1. Pose直接从OCR提取:")
print(f"   Keys: {list(pose_from_ocr.keys())}")
print(f"   altitude: {pose_from_ocr.get('altitude', 'MISSING')}")

# 添加到同步器
synchronizer = DataSynchronizer(buffer_size=100)
synchronizer.add_pose(pose_from_ocr)

# 从同步器获取
pose_from_sync = synchronizer.sync_frame_with_pose(0.0, 0)
print("\n2. Pose从同步器获取:")
if pose_from_sync:
    print(f"   Keys: {list(pose_from_sync.keys())}")
    print(f"   altitude: {pose_from_sync.get('altitude', 'MISSING')}")
else:
    print("   NONE - 同步器未返回pose")

cap.release()
