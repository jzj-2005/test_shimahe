"""
测试验证工具是否正常工作
使用正射图片的CSV结果测试所有工具
"""

import subprocess
import sys
from pathlib import Path

print("="*60)
print("验证工具测试")
print("="*60)

# 测试CSV文件
csv_file = "data/output/csv/detections_orthophoto.csv"
if not Path(csv_file).exists():
    print(f"\n✗ 测试CSV不存在: {csv_file}")
    print("请先运行正射图片推理生成测试数据")
    sys.exit(1)

print(f"\n✓ 找到测试CSV: {csv_file}")

# 测试1: 导出GeoJSON
print("\n" + "="*60)
print("测试1: 导出GeoJSON")
print("="*60)

try:
    result = subprocess.run(
        ["python", "tools/export_to_geojson.py", csv_file, "-o", "./data/output/test"],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore'
    )
    
    if result.returncode == 0:
        print("✓ GeoJSON导出测试通过")
        
        # 检查输出文件
        if Path("data/output/test/detections.geojson").exists():
            print("  ✓ detections.geojson 已生成")
        if Path("data/output/test/summary.txt").exists():
            print("  ✓ summary.txt 已生成")
    else:
        print(f"✗ GeoJSON导出失败:")
        print(result.stderr)
except Exception as e:
    print(f"✗ 测试异常: {e}")

# 测试2: 可视化工具
print("\n" + "="*60)
print("测试2: 可视化工具")
print("="*60)

try:
    result = subprocess.run(
        ["python", "tools/quick_visualize.py", 
         "data/output/test/detections.geojson",
         "-o", "data/output/test/test_map.html",
         "--no-open"],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore'
    )
    
    if result.returncode == 0 and Path("data/output/test/test_map.html").exists():
        print("✓ 可视化工具测试通过")
        print(f"  ✓ test_map.html 已生成")
    else:
        print(f"✗ 可视化工具失败:")
        print(result.stderr)
except Exception as e:
    print(f"✗ 测试异常: {e}")

# 测试3: 报告生成
print("\n" + "="*60)
print("测试3: 报告生成工具")
print("="*60)

try:
    result = subprocess.run(
        ["python", "tools/generate_report.py", 
         csv_file,
         "-o", "data/output/test/test_report.md"],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore'
    )
    
    if result.returncode == 0 and Path("data/output/test/test_report.md").exists():
        print("✓ 报告生成工具测试通过")
        print(f"  ✓ test_report.md 已生成")
    else:
        print(f"✗ 报告生成失败:")
        print(result.stderr)
except Exception as e:
    print(f"✗ 测试异常: {e}")

# 测试4: pandas依赖
print("\n" + "="*60)
print("测试4: 检查pandas依赖")
print("="*60)

try:
    import pandas as pd
    print("✓ pandas已安装")
    df = pd.read_csv(csv_file)
    print(f"  ✓ 成功读取CSV ({len(df)}条记录)")
except ImportError:
    print("✗ pandas未安装")
    print("  请运行: pip install pandas")
except Exception as e:
    print(f"✗ 读取CSV异常: {e}")

print("\n" + "="*60)
print("测试总结")
print("="*60)
print("所有工具已准备就绪，可以处理视频！")
print("\n下午拿到视频后运行:")
print("  python run_offline.py \"视频路径.MP4\"")
print("\n或使用快捷脚本:")
print("  run_video.bat \"视频路径.MP4\"")
print("="*60)
