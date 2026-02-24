"""
测试D:\Localsend\zhengshe目录中的图片是否有目标
"""
import cv2
import os
from ultralytics import YOLO
from pathlib import Path

print("=" * 60)
print("测试D:\\Localsend\\zhengshe目录图片检测")
print("=" * 60)

# 配置
MODEL_PATH = "./models/yolov11x.pt"
IMAGE_DIR = r"D:\Localsend\zhengshe"
CONFIDENCE = 0.25
IMGSZ = 1280

# 1. 加载模型
print(f"\n【步骤1】加载YOLO模型...")
model = YOLO(MODEL_PATH)
print(f"  ✓ 模型加载成功")

# 2. 获取图片列表
print(f"\n【步骤2】查找图片...")
image_files = sorted(list(Path(IMAGE_DIR).glob("*.jpeg")))[:10]  # 测试前10张
print(f"  找到 {len(image_files)} 张图片（测试前10张）")

# 3. 逐张检测
print(f"\n【步骤3】开始检测...\n")

total_detections = 0
for idx, img_path in enumerate(image_files, 1):
    print(f"[{idx}/{len(image_files)}] {img_path.name} ...", end=" ")
    
    # 读取图片
    image = cv2.imread(str(img_path))
    if image is None:
        print("✗ 无法读取")
        continue
    
    # YOLO检测
    results = model(
        image,
        conf=CONFIDENCE,
        iou=0.45,
        imgsz=IMGSZ,
        verbose=False
    )
    
    # 获取检测结果
    result = results[0]
    boxes = result.boxes
    num_detections = len(boxes)
    total_detections += num_detections
    
    if num_detections > 0:
        print(f"✓ 检测到 {num_detections} 个目标")
        for box in boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            cls_name = model.names[cls_id]
            print(f"    - {cls_name} ({conf:.2f})")
    else:
        print("- 无目标")

# 4. 总结
print("\n" + "=" * 60)
print(f"总计检测: {total_detections} 个目标")
print("=" * 60)
