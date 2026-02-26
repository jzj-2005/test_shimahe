"""
后处理功能测试脚本
测试智能去重、GeoJSON导出和地图生成功能

使用场景：
1. 验证新功能是否正常工作
2. 测试去重效果
3. 快速生成测试报告
"""

import sys
from pathlib import Path
import pandas as pd

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.output.deduplication import DetectionDeduplicator
from src.output.geojson_writer import GeoJSONWriter
from src.output.map_generator import MapGenerator
from src.output.post_processor import PostProcessor

print("=" * 70)
print("后处理功能测试")
print("=" * 70)

# 测试配置
test_config = {
    'export_geojson': True,
    'geojson_dir': './data/output/geojson/',
    'geojson_min_confidence': 0.0,
    'geojson_high_confidence': 0.7,
    
    'enable_deduplication': True,
    'deduplication': {
        'distance_threshold': 5.0,
        'prefer_non_edge': True,
        'prefer_rtk': True,
        'min_quality_score': 0.3,
        'edge_penalty': 0.5
    },
    
    'generate_map': True,
    'map_output_path': './data/output/map_test.html',
    'auto_open_map': False,
    
    'generate_summary': True,
    'summary_path': './data/output/summary_test.txt'
}

# 检查CSV文件
csv_path = './data/output/csv/detections_offline.csv'

if not Path(csv_path).exists():
    print(f"\n❌ CSV文件不存在: {csv_path}")
    print("\n请先运行检测生成CSV数据：")
    print("  python src/main.py --mode offline --video <视频文件>")
    sys.exit(1)

print(f"\n✓ 找到CSV文件: {csv_path}")

# 读取数据
print("\n[测试1] 读取CSV数据")
try:
    df = pd.read_csv(csv_path)
    print(f"  ✓ 读取成功: {len(df)} 条记录")
    
    # 显示数据概览
    print(f"\n  数据概览:")
    print(f"    - 帧号范围: {df['frame_number'].min()} ~ {df['frame_number'].max()}")
    print(f"    - 置信度范围: {df['confidence'].min():.3f} ~ {df['confidence'].max():.3f}")
    
    if 'gps_quality' in df.columns:
        print(f"    - GPS质量分布:")
        for quality, count in df['gps_quality'].value_counts().items():
            print(f"      {quality}: {count}")
    
except Exception as e:
    print(f"  ❌ 读取失败: {e}")
    sys.exit(1)

# 测试去重
print("\n[测试2] 智能去重")
try:
    deduplicator = DetectionDeduplicator(test_config['deduplication'])
    print(f"  ✓ 去重器初始化成功")
    
    df_unique = deduplicator.deduplicate_dataframe(df)
    print(f"  ✓ 去重完成:")
    print(f"    - 原始: {len(df)} 条")
    print(f"    - 去重后: {len(df_unique)} 条")
    print(f"    - 去除: {len(df) - len(df_unique)} 条")
    print(f"    - 去重率: {(len(df) - len(df_unique)) / len(df) * 100:.1f}%")
    
except Exception as e:
    print(f"  ❌ 去重失败: {e}")
    df_unique = df

# 测试GeoJSON导出
print("\n[测试3] GeoJSON导出")
try:
    geojson_writer = GeoJSONWriter(test_config)
    print(f"  ✓ GeoJSON写入器初始化成功")
    
    geojson_files = geojson_writer.export_multiple(
        df_raw=df,
        df_unique=df_unique,
        output_dir='./data/output/geojson/'
    )
    
    print(f"  ✓ 导出完成:")
    for file_type, file_path in geojson_files.items():
        file_size = Path(file_path).stat().st_size / 1024
        print(f"    - {file_type}: {file_path} ({file_size:.1f}KB)")
    
except Exception as e:
    print(f"  ❌ GeoJSON导出失败: {e}")
    geojson_files = {}

# 测试地图生成
print("\n[测试4] HTML地图生成")
try:
    map_generator = MapGenerator(test_config)
    print(f"  ✓ 地图生成器初始化成功")
    
    if geojson_files.get('unique'):
        map_file = map_generator.generate(
            geojson_files['unique'],
            './data/output/map_test.html'
        )
        
        if map_file:
            map_size = Path(map_file).stat().st_size / 1024
            print(f"  ✓ 地图生成完成: {map_file} ({map_size:.1f}KB)")
        else:
            print(f"  ❌ 地图生成失败")
    else:
        print(f"  ⚠️  跳过地图生成（GeoJSON未生成）")
        
except Exception as e:
    print(f"  ❌ 地图生成失败: {e}")

# 测试完整后处理流程
print("\n[测试5] 完整后处理流程")
try:
    post_processor = PostProcessor(test_config)
    print(f"  ✓ 后处理器初始化成功")
    
    results = post_processor.process(
        csv_path=csv_path,
        output_base_dir='./data/output/'
    )
    
    if results.get('success'):
        print(f"  ✓ 后处理流程执行成功")
        print(f"\n  生成的文件:")
        for file_type, file_info in results.get('files', {}).items():
            if isinstance(file_info, dict):
                for sub_type, path in file_info.items():
                    print(f"    - {file_type}.{sub_type}: {path}")
            else:
                print(f"    - {file_type}: {file_info}")
        
        if results.get('deduplication'):
            dedup_info = results['deduplication']
            print(f"\n  去重统计:")
            print(f"    - 原始: {dedup_info['original']}")
            print(f"    - 去重后: {dedup_info['unique']}")
            print(f"    - 去重率: {dedup_info['removal_rate']:.1f}%")
    else:
        print(f"  ❌ 后处理流程失败")
        if 'error' in results:
            print(f"    错误: {results['error']}")
        
except Exception as e:
    print(f"  ❌ 后处理流程失败: {e}")
    import traceback
    traceback.print_exc()

# 总结
print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)

print("\n下一步:")
print("  1. 查看生成的地图:")
print("     start data/output/map_test.html")
print("")
print("  2. 查看统计摘要:")
print("     notepad data/output/summary_test.txt")
print("")
print("  3. 在QGIS中验证GeoJSON:")
print("     图层 → 添加矢量图层 → data/output/geojson/detections_unique.geojson")
print("")
print("  4. 如果测试通过，运行完整检测:")
print("     python src/main.py --mode offline --video <你的视频文件>")

print("\n" + "=" * 70)
