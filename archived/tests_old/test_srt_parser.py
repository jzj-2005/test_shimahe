"""
SRT解析器测试
"""

import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.input.srt_parser import SRTParser


def test_srt_parser():
    """测试SRT解析器"""
    print("="*60)
    print("测试SRT解析器")
    print("="*60)
    
    # 创建测试SRT内容
    test_srt_content = """1
00:00:00,000 --> 00:00:00,033
<font size="28">FrameCnt: 1, DiffTime: 33ms
2024-01-15 10:30:15.123
[latitude: 31.234567] [longitude: 121.456789] [altitude: 120.5m]
</font>

2
00:00:00,033 --> 00:00:00,066
<font size="28">FrameCnt: 2, DiffTime: 33ms
2024-01-15 10:30:15.156
[latitude: 31.234568] [longitude: 121.456790] [altitude: 120.6m]
</font>
"""
    
    # 创建临时SRT文件
    test_srt_path = Path("./tests/test_data.srt")
    test_srt_path.parent.mkdir(exist_ok=True)
    
    with open(test_srt_path, 'w', encoding='utf-8') as f:
        f.write(test_srt_content)
    
    # 测试解析
    parser = SRTParser()
    pose_data = parser.parse(str(test_srt_path))
    
    print(f"\n解析结果: 共{len(pose_data)}条位姿数据")
    
    # 打印前几条
    parser.print_sample(count=2)
    
    # 测试查询
    print("\n--- 测试时间戳查询 ---")
    pose = parser.get_pose_by_timestamp(0.0, tolerance=100.0)
    if pose:
        print(f"找到位姿: GPS({pose['latitude']:.6f}, {pose['longitude']:.6f})")
    
    # 清理测试文件
    test_srt_path.unlink()
    
    print("\n测试完成!")


if __name__ == '__main__':
    test_srt_parser()
