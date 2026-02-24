import pandas as pd
import math

df = pd.read_csv('data/output/csv/detections_orthophoto.csv')

# 从camera_params.yaml读取参数
meters_per_degree_lat = 110540  # 每度纬度对应的米数
meters_per_degree_lon = 111320  # 每度经度对应的米数（赤道）

# 检查东莞的位置（约北纬22.77-22.79度）
print('=== 东莞市区位置参考 ===')
print('东莞市中心大约: 北纬23.05°, 东经113.75°')
print()

print('=== 数据位置信息 ===')
avg_drone_lat = df["drone_lat"].mean()
avg_drone_lon = df["drone_lon"].mean()
print(f'无人机平均位置: 北纬{avg_drone_lat:.6f}°, 东经{avg_drone_lon:.6f}°')
print(f'纬度范围: {df["drone_lat"].min():.6f}° ~ {df["drone_lat"].max():.6f}°')
print(f'经度范围: {df["drone_lon"].min():.6f}° ~ {df["drone_lon"].max():.6f}°')
print()

# 计算实际偏差距离
print('=== 目标偏离无人机位置的距离统计 ===')
sample_df = df.head(20)

for idx, row in sample_df.iterrows():
    drone_lat = row['drone_lat']
    drone_lon = row['drone_lon']
    center_lat = row['center_lat']
    center_lon = row['center_lon']
    
    # 计算距离（米）
    lat_diff_m = (center_lat - drone_lat) * meters_per_degree_lat
    lon_diff_m = (center_lon - drone_lon) * meters_per_degree_lon * math.cos(math.radians(drone_lat))
    
    distance = math.sqrt(lat_diff_m**2 + lon_diff_m**2)
    
    if idx < 5:  # 只打印前5条
        print(f'检测{idx+1}: 南北偏移={lat_diff_m:+.1f}m, 东西偏移={lon_diff_m:+.1f}m, 距离={distance:.1f}m')

print()

# 统计全部数据
df['lat_diff_m'] = (df['center_lat'] - df['drone_lat']) * meters_per_degree_lat
df['lon_diff_m'] = (df['center_lon'] - df['drone_lon']) * meters_per_degree_lon * df['drone_lat'].apply(lambda x: math.cos(math.radians(x)))
df['distance_m'] = (df['lat_diff_m']**2 + df['lon_diff_m']**2)**0.5

print('=== 全部检测的偏移距离统计 ===')
print(f'最小距离: {df["distance_m"].min():.1f}m')
print(f'最大距离: {df["distance_m"].max():.1f}m')
print(f'平均距离: {df["distance_m"].mean():.1f}m')
print(f'中位数距离: {df["distance_m"].median():.1f}m')
print()

# 统计方向性偏差
print('=== 偏移方向分析 ===')
print(f'南北偏移: {df["lat_diff_m"].mean():+.1f}m (平均), {df["lat_diff_m"].median():+.1f}m (中位数)')
print(f'东西偏移: {df["lon_diff_m"].mean():+.1f}m (平均), {df["lon_diff_m"].median():+.1f}m (中位数)')
print()

# 检查相机参数计算
print('=== 相机参数验证 ===')
avg_altitude = df['altitude'].mean()
print(f'平均飞行高度: {avg_altitude:.1f}m')

# 相机参数（从camera_params.yaml）
image_width = 5472
image_height = 3648
sensor_width = 13.2  # mm
sensor_height = 8.8  # mm
focal_length = 8.8   # mm

# 计算GSD
gsd_x = (sensor_width * avg_altitude) / (focal_length * image_width)
gsd_y = (sensor_height * avg_altitude) / (focal_length * image_height)
print(f'计算的GSD: X方向={gsd_x:.4f}m/pixel, Y方向={gsd_y:.4f}m/pixel')

# 计算理论覆盖范围
ground_width = gsd_x * image_width
ground_height = gsd_y * image_height
print(f'单张图片地面覆盖: {ground_width:.1f}m × {ground_height:.1f}m')
