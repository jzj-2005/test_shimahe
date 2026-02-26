"""
v2.1功能安装验证脚本
验证所有新增模块和配置是否正确

运行此脚本确认v2.1功能已正确安装
"""

import sys
import os
from pathlib import Path

print("=" * 70)
print("石马河四乱检测系统 v2.1 安装验证")
print("=" * 70)
print()

# 验证结果
results = {
    'success': [],
    'warning': [],
    'error': []
}

def check(name, condition, error_msg=""):
    """检查项目"""
    if condition:
        print(f"[OK] {name}")
        results['success'].append(name)
        return True
    else:
        print(f"[FAIL] {name}")
        if error_msg:
            print(f"   {error_msg}")
        results['error'].append(name)
        return False

def warn(name, msg=""):
    """警告项目"""
    print(f"[WARN] {name}")
    if msg:
        print(f"   {msg}")
    results['warning'].append(name)

# 1. 检查Python版本
print("[1/8] 检查Python环境")
print("-" * 70)
py_version = sys.version_info
check(
    f"Python版本 {py_version.major}.{py_version.minor}",
    py_version >= (3, 8),
    "需要Python 3.8或更高版本"
)
print()

# 2. 检查新增模块文件
print("[2/8] 检查新增源代码文件")
print("-" * 70)
new_files = [
    'src/output/deduplication.py',
    'src/output/geojson_writer.py',
    'src/output/map_generator.py',
    'src/output/post_processor.py'
]

for file in new_files:
    check(
        f"文件存在: {file}",
        Path(file).exists(),
        f"文件不存在: {file}"
    )
print()

# 3. 检查模块导入
print("[3/8] 检查模块导入")
print("-" * 70)

try:
    from src.output import DetectionDeduplicator
    check("DetectionDeduplicator", True)
except Exception as e:
    check("DetectionDeduplicator", False, str(e))

try:
    from src.output import GeoJSONWriter
    check("GeoJSONWriter", True)
except Exception as e:
    check("GeoJSONWriter", False, str(e))

try:
    from src.output import MapGenerator
    check("MapGenerator", True)
except Exception as e:
    check("MapGenerator", False, str(e))

try:
    from src.output import PostProcessor
    check("PostProcessor", True)
except Exception as e:
    check("PostProcessor", False, str(e))

print()

# 4. 检查配置文件
print("[4/8] 检查配置文件更新")
print("-" * 70)

config_files = {
    'config/offline_config.yaml': [
        'export_geojson',
        'enable_deduplication',
        'generate_map',
        'generate_summary'
    ],
    'config/realtime_config.yaml': [
        'export_geojson',
        'enable_deduplication',
        'generate_map',
        'generate_summary'
    ]
}

for config_file, keys in config_files.items():
    if Path(config_file).exists():
        try:
            import yaml
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            output_config = config.get('output', {})
            missing_keys = [k for k in keys if k not in output_config]
            
            if not missing_keys:
                check(f"配置完整: {config_file}", True)
            else:
                warn(
                    f"配置不完整: {config_file}",
                    f"缺少配置项: {', '.join(missing_keys)}"
                )
        except Exception as e:
            warn(f"配置文件读取失败: {config_file}", str(e))
    else:
        check(f"配置文件存在: {config_file}", False)

print()

# 5. 检查依赖库
print("[5/8] 检查依赖库")
print("-" * 70)

dependencies = [
    ('pandas', '数据处理'),
    ('numpy', '数值计算'),
    ('yaml', '配置读取'),
    ('loguru', '日志记录')
]

for module, desc in dependencies:
    try:
        __import__(module)
        check(f"{module} ({desc})", True)
    except ImportError:
        check(
            f"{module} ({desc})", 
            False,
            f"请运行: pip install {module}"
        )

print()

# 6. 检查文档文件
print("[6/8] 检查文档文件")
print("-" * 70)

doc_files = [
    'GeoJSON输出和智能去重实现文档.md',
    'GeoJSON和地图输出使用指南.md',
    'v2.1功能快速启动指南.md',
    'CHANGELOG_v2.1.md',
    'v2.1实施完成报告.md',
    'v2.1实施清单.md'
]

for doc in doc_files:
    check(
        f"文档: {doc}",
        Path(doc).exists()
    )

print()

# 7. 检查测试脚本
print("[7/8] 检查测试脚本")
print("-" * 70)

test_files = [
    'test_post_processing.py',
    'test_v2.1_features.bat'
]

for test_file in test_files:
    check(
        f"测试脚本: {test_file}",
        Path(test_file).exists()
    )

print()

# 8. 功能测试
print("[8/8] 功能快速测试")
print("-" * 70)

try:
    # 测试去重器
    dedup = DetectionDeduplicator({'distance_threshold': 5.0})
    distance = dedup._haversine_distance(23.0, 114.0, 23.0001, 114.0001)
    check(
        "去重器距离计算",
        10 < distance < 20,  # 应该约15米
        f"计算结果异常: {distance}米"
    )
    
    # 测试质量评分
    score = dedup._calculate_quality_score({
        'confidence': 0.8,
        'is_on_edge': False,
        'gps_quality': 'RTK'
    })
    check(
        "去重器质量评分",
        0.9 < score < 1.0,  # 0.8 × 1.0 × 1.2 = 0.96
        f"评分异常: {score}"
    )
    
except Exception as e:
    check("去重器功能测试", False, str(e))

try:
    # 测试GeoJSON写入器
    geojson_writer = GeoJSONWriter({
        'geojson_dir': './data/output/geojson/',
        'geojson_min_confidence': 0.0,
        'geojson_high_confidence': 0.7
    })
    check("GeoJSON写入器初始化", True)
except Exception as e:
    check("GeoJSON写入器初始化", False, str(e))

try:
    # 测试地图生成器
    map_gen = MapGenerator({})
    check("地图生成器初始化", True)
except Exception as e:
    check("地图生成器初始化", False, str(e))

try:
    # 测试后处理器
    post_proc = PostProcessor({
        'export_geojson': True,
        'enable_deduplication': True,
        'generate_map': True,
        'generate_summary': True,
        'deduplication': {'distance_threshold': 5.0}
    })
    check("后处理器初始化", True)
    check("后处理器功能检查", post_proc.is_enabled())
except Exception as e:
    check("后处理器初始化", False, str(e))

print()

# 总结
print("=" * 70)
print("验证结果总结")
print("=" * 70)
print()

total = len(results['success']) + len(results['warning']) + len(results['error'])

print(f"[OK] Success: {len(results['success'])} items")
print(f"[WARN] Warnings: {len(results['warning'])} items")
print(f"[FAIL] Errors: {len(results['error'])} items")
print()

if results['error']:
    print("Error items:")
    for item in results['error']:
        print(f"  - {item}")
    print()
    print("[FAIL] Verification failed! Please fix the errors above and run again")
    print()
    sys.exit(1)

if results['warning']:
    print("Warning items:")
    for item in results['warning']:
        print(f"  - {item}")
    print()
    print("[WARN] Verification passed with warnings, please check")
    print()

if not results['error']:
    print("=" * 70)
    print("[SUCCESS] v2.1 Installation Verification Passed!")
    print("=" * 70)
    print()
    print("System ready! New features available:")
    print()
    print("  [OK] Smart Deduplication")
    print("  [OK] GeoJSON Auto Export")
    print("  [OK] HTML Map Generation")
    print("  [OK] Statistics Summary")
    print()
    print("Next steps:")
    print("  1. Read quick start guide: v2.1功能快速启动指南.md")
    print("  2. Run test: python test_post_processing.py")
    print("  3. Run detection: python src/main.py --mode offline --video <video_file>")
    print()
    print("Documentation:")
    print("  - Technical: GeoJSON输出和智能去重实现文档.md")
    print("  - User Guide: GeoJSON和地图输出使用指南.md")
    print()
    print("=" * 70)
    sys.exit(0)
