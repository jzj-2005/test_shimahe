"""
运行前环境检查脚本
检查所有必要的配置和依赖是否就绪
"""

import sys
from pathlib import Path
import yaml

print("=" * 70)
print("石马河四乱实时检测系统 - 启动前检查")
print("=" * 70)

issues = []
warnings = []
success_items = []

# 1. 检查配置文件
print("\n[1/7] 检查配置文件...")
config_files = [
    "config/realtime_config.yaml",
    "config/camera_params.yaml",
    "config/detection_config.yaml",
    "config/classes_config.yaml"
]

for config_file in config_files:
    if Path(config_file).exists():
        success_items.append(f"✓ 配置文件存在: {config_file}")
    else:
        issues.append(f"❌ 配置文件不存在: {config_file}")

# 2. 检查MQTT配置
print("[2/7] 检查MQTT配置...")
try:
    with open("config/realtime_config.yaml", 'r', encoding='utf-8') as f:
        realtime_config = yaml.safe_load(f)
    
    mqtt_config = realtime_config.get('mqtt', {})
    
    # 检查关键参数
    username = mqtt_config.get('username', '')
    password = mqtt_config.get('password', '')
    aircraft_topic = mqtt_config.get('topics', {}).get('aircraft_state', '')
    
    if '[请填写' in username or username == '':
        issues.append("❌ MQTT username未配置（需要DJI App Key）")
    else:
        success_items.append(f"✓ MQTT username已配置")
    
    if '[请填写' in password or password == '':
        issues.append("❌ MQTT password未配置（需要DJI App Secret）")
    else:
        success_items.append(f"✓ MQTT password已配置")
    
    if '[请填写' in aircraft_topic or aircraft_topic == '':
        issues.append("❌ MQTT主题未配置（需要设备SN）")
    else:
        success_items.append(f"✓ MQTT主题已配置: {aircraft_topic}")
    
except Exception as e:
    issues.append(f"❌ 读取MQTT配置失败: {e}")

# 3. 检查RTSP配置
print("[3/7] 检查RTSP配置...")
try:
    rtsp_config = realtime_config.get('rtsp', {})
    rtsp_url = rtsp_config.get('url', '')
    
    if 'rtsp://' not in rtsp_url:
        issues.append("❌ RTSP URL格式不正确")
    elif '192.168.1.100' in rtsp_url or 'localhost' in rtsp_url:
        warnings.append("⚠️  RTSP URL可能是示例地址，请确认是否为实际地址")
        success_items.append(f"✓ RTSP URL已配置: {rtsp_url}")
    else:
        success_items.append(f"✓ RTSP URL已配置: {rtsp_url}")
        
except Exception as e:
    issues.append(f"❌ 读取RTSP配置失败: {e}")

# 4. 检查相机参数
print("[4/7] 检查相机参数...")
try:
    with open("config/camera_params.yaml", 'r', encoding='utf-8') as f:
        camera_config = yaml.safe_load(f)
    
    camera = camera_config.get('camera', {})
    resolution = camera.get('resolution', {})
    width = resolution.get('width', 0)
    height = resolution.get('height', 0)
    focal_length = camera.get('focal_length', 0)
    
    if width > 0 and height > 0:
        success_items.append(f"✓ 相机分辨率: {width}x{height}")
    else:
        issues.append("❌ 相机分辨率无效")
    
    if focal_length > 0:
        success_items.append(f"✓ 焦距: {focal_length}mm")
    else:
        issues.append("❌ 焦距无效")
        
except Exception as e:
    issues.append(f"❌ 读取相机配置失败: {e}")

# 5. 检查YOLO模型
print("[5/7] 检查YOLO模型...")
try:
    with open("config/detection_config.yaml", 'r', encoding='utf-8') as f:
        detection_config = yaml.safe_load(f)
    
    model_path = detection_config.get('detection', {}).get('model_path', '')
    
    if Path(model_path).exists():
        model_size = Path(model_path).stat().st_size / (1024*1024)  # MB
        success_items.append(f"✓ YOLO模型存在: {model_path} ({model_size:.1f}MB)")
    else:
        issues.append(f"❌ YOLO模型不存在: {model_path}")
        
except Exception as e:
    issues.append(f"❌ 检查模型失败: {e}")

# 6. 检查Python依赖
print("[6/7] 检查Python依赖...")
required_packages = {
    'torch': 'PyTorch',
    'ultralytics': 'YOLOv11',
    'cv2': 'OpenCV',
    'numpy': 'NumPy',
    'paho.mqtt': 'MQTT客户端',
    'loguru': '日志库',
    'yaml': 'YAML解析'
}

missing_packages = []
for package, name in required_packages.items():
    try:
        if package == 'cv2':
            import cv2
        elif package == 'paho.mqtt':
            import paho.mqtt.client
        elif package == 'yaml':
            import yaml
        else:
            __import__(package)
        success_items.append(f"✓ {name}已安装")
    except ImportError:
        missing_packages.append(name)
        issues.append(f"❌ {name}未安装")

# 7. 检查输出目录
print("[7/7] 检查输出目录...")
output_dirs = [
    "data/output/csv",
    "data/output/images",
    "data/output/error_frames"
]

for dir_path in output_dirs:
    path = Path(dir_path)
    if not path.exists():
        warnings.append(f"⚠️  输出目录不存在（程序会自动创建）: {dir_path}")
    else:
        success_items.append(f"✓ 输出目录存在: {dir_path}")

# 输出检查结果
print("\n" + "=" * 70)
print("检查结果汇总")
print("=" * 70)

if success_items:
    print("\n✅ 通过的检查项:")
    for item in success_items:
        print(f"  {item}")

if warnings:
    print("\n⚠️  警告（不影响运行）:")
    for warning in warnings:
        print(f"  {warning}")

if issues:
    print("\n❌ 发现问题（需要修复）:")
    for issue in issues:
        print(f"  {issue}")
    
    print("\n" + "=" * 70)
    print("❌ 检查未通过，请先解决以上问题再运行程序")
    print("=" * 70)
    
    # 输出修复建议
    if any("MQTT" in issue for issue in issues):
        print("\n💡 MQTT配置修复指南:")
        print("  1. 访问 https://developer.dji.com/")
        print("  2. 创建应用获取 App Key 和 App Secret")
        print("  3. 在 config/realtime_config.yaml 中填写")
        print("  4. 替换设备SN到MQTT主题中")
    
    if any("模型" in issue for issue in issues):
        print("\n💡 模型文件修复指南:")
        print("  1. 下载 YOLOv11x 模型")
        print("  2. 或从 https://github.com/ultralytics/assets/releases 下载")
        print("  3. 放置到 models/ 目录下")
    
    if missing_packages:
        print("\n💡 安装缺失的依赖:")
        print("  pip install -r requirements.txt")
    
    sys.exit(1)
else:
    print("\n" + "=" * 70)
    print("✅ 所有检查通过！可以启动程序了")
    print("=" * 70)
    print("\n启动命令:")
    print("  python run_realtime.py")
    print("  或")
    print("  python src/main.py --mode realtime")
    print("\n按 ESC 键可以随时退出程序")
    print("=" * 70)
    sys.exit(0)
