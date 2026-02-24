import pandas as pd

df = pd.read_csv('data/output/csv/detections_orthophoto.csv')

print('无人机位置统计:')
print(f'纬度范围: {df["drone_lat"].min():.6f} ~ {df["drone_lat"].max():.6f}')
print(f'经度范围: {df["drone_lon"].min():.6f} ~ {df["drone_lon"].max():.6f}')
print(f'高度范围: {df["altitude"].min():.1f} ~ {df["altitude"].max():.1f}m')
print()

print('检测目标中心位置统计:')
print(f'纬度范围: {df["center_lat"].min():.6f} ~ {df["center_lat"].max():.6f}')
print(f'经度范围: {df["center_lon"].min():.6f} ~ {df["center_lon"].max():.6f}')
print()

print('前5条检测数据样本:')
print(df[["drone_lat", "drone_lon", "altitude", "center_lat", "center_lon"]].head(5).to_string(index=False))
print()

print('飞机与目标的距离偏差统计:')
df['lat_diff'] = abs(df['center_lat'] - df['drone_lat'])
df['lon_diff'] = abs(df['center_lon'] - df['drone_lon'])
print(f'纬度差范围: {df["lat_diff"].min():.6f} ~ {df["lat_diff"].max():.6f}')
print(f'经度差范围: {df["lon_diff"].min():.6f} ~ {df["lon_diff"].max():.6f}')
