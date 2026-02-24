"""
分析当前坐标解算的误差来源
"""

# 当前参数
sensor_width = 13.2  # mm
focal_length = 8.8   # mm
altitude = 139       # 米
image_width = 5472   # 像素

# 计算GSD
gsd = (sensor_width * altitude) / (focal_length * image_width)

print("="*60)
print("当前坐标解算误差分析")
print("="*60)

print("\n1. 地面分辨率 (GSD)")
print(f"   当前GSD: {gsd*100:.2f} 厘米/像素")
print(f"   图像覆盖范围: {gsd*image_width:.1f}米 × {gsd*3648:.1f}米")

print("\n2. 相机参数误差影响")
# 焦距误差
focal_error = 0.2  # mm
gsd_focal_error = ((focal_length - focal_error) / focal_length - 1) * gsd * image_width / 2
print(f"   焦距误差±0.2mm → 坐标误差±{abs(gsd_focal_error):.2f}米")

# 传感器尺寸误差
sensor_error = 0.3  # mm
gsd_sensor_error = (sensor_error / sensor_width) * gsd * image_width / 2
print(f"   传感器尺寸误差±0.3mm → 坐标误差±{gsd_sensor_error:.2f}米")

print("\n3. 姿态角误差影响")
import math
for angle in [1, 2, 3]:
    offset = altitude * math.tan(math.radians(angle))
    print(f"   俯仰/翻滚±{angle}° → 坐标误差±{offset:.2f}米")

print("\n4. 时间同步误差影响")
time_diff = 19.67  # 秒
for speed in [5, 10, 15]:
    position_error = time_diff * speed
    print(f"   飞行速度{speed}m/s × 时间差19.67s → 位置偏移{position_error:.1f}米")

print("\n5. GPS本身精度")
print(f"   RTK定位精度: 约±0.02-0.05米（厘米级）")
print(f"   相对于其他误差源，GPS误差可忽略")

print("\n" + "="*60)
print("误差源排序（从大到小）:")
print("="*60)
print("1. 时间同步误差:    可能达到 50-200米 ⚠⚠⚠ 最严重")
print("2. 姿态角误差:      约 2-7米")  
print("3. 相机参数误差:    约 1-3米")
print("4. GPS定位误差:     约 0.02-0.05米（可忽略）")
print("\n总预期误差: 如果时间同步问题未解决，误差可达 50-200米")
print("            如果时间同步正确，误差约 3-10米")
print("="*60)
