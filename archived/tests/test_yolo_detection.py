"""
简单的YOLO检测测试脚本
用于验证模型在正射图片上的检测效果
"""
import cv2
import os
from ultralytics import YOLO
from pathlib import Path

print("=" * 60)
print("YOLO模型检测测试")
print("=" * 60)

# 配置
MODEL_PATH = "./models/yolov11x.pt"
IMAGE_DIR = r"D:/jzj/siluan_new/test_siluan_img"
OUTPUT_DIR = "./data/output/test_detections"

# 检测参数（可以调整）
CONFIDENCE = 0.25  # 置信度阈值
IOU = 0.45         # IoU阈值
IMGSZ = 1280       # 输入图像尺寸

# 创建输出目录
os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"\n【配置】")
print(f"  模型: {MODEL_PATH}")
print(f"  图片目录: {IMAGE_DIR}")
print(f"  置信度阈值: {CONFIDENCE}")
print(f"  输入尺寸: {IMGSZ}")

# 1. 加载模型
print(f"\n【步骤1】加载YOLO模型...")
model = YOLO(MODEL_PATH)
print(f"  ✓ 模型加载成功")
print(f"  模型类别: {model.names}")

# 2. 获取图片列表
print(f"\n【步骤2】查找图片...")
image_files = list(Path(IMAGE_DIR).glob("*.jpeg"))[:5]  # 只测试前5张
print(f"  找到 {len(image_files)} 张图片（测试前5张）")

# 3. 逐张检测
print(f"\n【步骤3】开始检测...\n")

total_detections = 0
for idx, img_path in enumerate(image_files, 1):
    print(f"[{idx}/{len(image_files)}] 处理: {img_path.name}")
    
    # 读取图片
    image = cv2.imread(str(img_path))
    if image is None:
        print(f"  ✗ 无法读取图片")
        continue
    
    print(f"  图片尺寸: {image.shape[1]}x{image.shape[0]}")
    
    # YOLO检测
    results = model(
        image,
        conf=CONFIDENCE,
        iou=IOU,
        imgsz=IMGSZ,
        verbose=False
    )
    
    # 获取检测结果
    result = results[0]
    boxes = result.boxes
    num_detections = len(boxes)
    total_detections += num_detections
    
    print(f"  检测到 {num_detections} 个目标")
    
    # 显示详细信息
    if num_detections > 0:
        for i, box in enumerate(boxes):
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            cls_name = model.names[cls_id]
            print(f"    [{i+1}] {cls_name} (置信度: {conf:.2f})")
        
        # 保存标注结果
        annotated = result.plot()
        output_path = Path(OUTPUT_DIR) / f"detected_{img_path.name}"
        cv2.imwrite(str(output_path), annotated)
        print(f"  ✓ 已保存标注图: {output_path}")
    else:
        print(f"  - 未检测到目标")
    
    print()

# 4. 总结
print("=" * 60)
print(f"检测完成！")
print(f"  总计检测: {total_detections} 个目标")
print(f"  结果保存: {OUTPUT_DIR}")
print("=" * 60)

# 如果没有检测到任何目标，给出建议
if total_detections == 0:
    print("\n⚠️ 提示: 未检测到任何目标，可能的原因：")
    print("  1. 模型不适合正射图片（训练数据是普通航拍/倾斜摄影）")
    print("  2. 图片中确实没有违建、垃圾等目标")
    print("  3. 置信度阈值过高（当前0.25，可以降到0.1试试）")
    print("  4. 模型需要用正射图片数据重新训练")
    print("\n建议: 用一张已知有目标的图片测试，或降低置信度阈值")
