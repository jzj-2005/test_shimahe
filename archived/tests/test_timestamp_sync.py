"""
测试时间戳同步逻辑
"""
import sys
from datetime import datetime, timedelta, timezone

# 清除所有模块缓存
for module in list(sys.modules.keys()):
    if module.startswith('src.'):
        del sys.modules[module]

from src.input.mrk_parser import MRKParser
from src.input.image_sequence_reader import ImageSequenceReader

print("=" * 60)
print("时间戳同步测试")
print("=" * 60)

# 1. 测试MRK解析
print("\n【测试1】MRK文件解析")
mrk_file = r"D:\Localsend\zhengshe\DJI_20260204142623_0002_D.MRK"
parser = MRKParser()
pose_data = parser.parse(mrk_file)
print(f"解析到 {len(pose_data)} 条位姿数据")

first_pose = pose_data[0]
print(f"\n第一个GPS数据:")
print(f"  GPS时间: {first_pose['gps_time']}s")
print(f"  时间戳: {first_pose['timestamp']}ms")
print(f"  UTC时间: {datetime.fromtimestamp(first_pose['timestamp']/1000, tz=timezone.utc)}")

# 2. 测试图片时间戳提取
print("\n【测试2】图片时间戳提取")
reader = ImageSequenceReader(r"D:\Localsend\zhengshe")
reader.open()

# 读取第一张图片
success, image, metadata = reader.read()
if success:
    print(f"第一张图片: {metadata['filename']}")
    print(f"  时间戳: {metadata['timestamp']}ms")
    print(f"  UTC时间: {datetime.fromtimestamp(metadata['timestamp']/1000, tz=timezone.utc)}")
    
    # 3. 计算时间差
    print("\n【测试3】时间差计算")
    time_diff = abs(first_pose['timestamp'] - metadata['timestamp'])
    print(f"  时间差: {time_diff}ms = {time_diff/1000}秒")
    
    if time_diff < 5000:  # 5秒容差
        print(f"  ✓ 可以匹配！（容差5秒）")
    else:
        print(f"  ✗ 无法匹配（超过容差）")

# 4. 测试同步器
print("\n【测试4】DataSynchronizer同步测试")
from src.utils.data_sync import DataSynchronizer

sync = DataSynchronizer(sync_method='timestamp', timestamp_tolerance=5000.0)

# 添加所有位姿数据
for pose in pose_data:
    sync.add_pose(pose)

print(f"  位姿缓冲区大小: {len(sync.pose_buffer)}")

# 尝试同步第一张图片
result = sync.sync_frame_with_pose(metadata['timestamp'], 0)
if result:
    print(f"  ✓ 同步成功！")
else:
    print(f"  ✗ 同步失败")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
