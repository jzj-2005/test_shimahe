"""检查正射图片的实际尺寸"""
import cv2
import glob
import os

image_dir = r"D:\Localsend\zhengshe"
image_files = sorted(glob.glob(os.path.join(image_dir, "*.jpeg")))

if not image_files:
    print("未找到JPEG图片")
    exit()

print(f"找到 {len(image_files)} 张图片")
print("\n前5张图片尺寸:")
for i, img_path in enumerate(image_files[:5]):
    img = cv2.imread(img_path)
    if img is not None:
        print(f"{os.path.basename(img_path)}: {img.shape}")
    else:
        print(f"{os.path.basename(img_path)}: 无法读取")
