"""
测试主流程是否能在test_siluan_img图片上检测到目标
"""
import cv2
import os
from src.detection.yolo_detector import YOLODetector

print("=" * 60)
print("测试主流程检测器")
print("=" * 60)

# 使用和test_yolo_detection.py相同的图片
TEST_IMAGE = r"D:\jzj\siluan_new\test_siluan_img\DJI_20260204142844_0078_V.jpeg"

print(f"\n测试图片: {os.path.basename(TEST_IMAGE)}")

# 读取图片
image = cv2.imread(TEST_IMAGE)
if image is None:
    print("✗ 无法读取图片")
    exit(1)

print(f"图片尺寸: {image.shape}")

# 初始化检测器（使用和主流程相同的配置）
detector = YOLODetector(
    model_path="./models/yolov11x.pt",
    confidence_threshold=0.25,
    iou_threshold=0.45,
    device="cuda",
    half_precision=False,
    imgsz=1280
)

print(f"\n开始检测...")

# 检测
detections = detector.detect(
    image,
    return_type='corners',
    check_edge=True,
    edge_threshold=50
)

print(f"\n检测结果: {len(detections)} 个目标")

if detections:
    for i, det in enumerate(detections, 1):
        print(f"  [{i}] 类别:{det['class_name']} 置信度:{det['confidence']:.2f}")
else:
    print("  未检测到目标")

print("\n" + "=" * 60)
