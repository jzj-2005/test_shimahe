"""
检查YOLO模型的实际类别名称
"""
from ultralytics import YOLO

MODEL_PATH = "./models/yolov11x.pt"

print("=" * 60)
print("检查YOLO模型类别")
print("=" * 60)

# 加载模型
model = YOLO(MODEL_PATH)

# 获取类别名称
print(f"\n模型类别数量: {len(model.names)}")
print(f"\n模型类别映射:")
print("-" * 60)

for class_id, class_name in model.names.items():
    print(f"  {class_id}: {class_name}")

print("\n" + "=" * 60)
