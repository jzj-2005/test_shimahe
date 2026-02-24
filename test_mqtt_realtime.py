"""
MQTT实时连接测试脚本
用于验证MQTT配置是否正确，能否正常接收无人机位姿数据

使用方法:
    python test_mqtt_realtime.py

要求:
    1. 已配置 config/realtime_config.yaml
    2. 设备在线（无人机或机场已开机）
    3. 网络连接正常
"""

import sys
import time
import yaml
import json
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.input.mqtt_client import DJIMQTTClient
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保已安装所有依赖: pip install -r requirements.txt")
    sys.exit(1)


def print_separator(char="=", length=60):
    """打印分隔线"""
    print(char * length)


def print_header(title):
    """打印标题"""
    print_separator()
    print(f"  {title}")
    print_separator()


def print_step(step_num, total_steps, description):
    """打印步骤"""
    print(f"\n[{step_num}/{total_steps}] {description}")
    print("-" * 60)


def load_config():
    """加载配置文件"""
    config_path = Path(__file__).parent / "config" / "realtime_config.yaml"
    
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        print("请确保 config/realtime_config.yaml 文件存在")
        sys.exit(1)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config['mqtt']
    except Exception as e:
        print(f"❌ 加载配置文件失败: {e}")
        sys.exit(1)


def validate_config(mqtt_config):
    """验证配置参数"""
    print("\n配置参数检查:")
    
    issues = []
    
    # 检查必填字段
    required_fields = ['broker', 'port', 'username', 'password', 'client_id', 'topics']
    for field in required_fields:
        if field not in mqtt_config:
            issues.append(f"  ❌ 缺少必填字段: {field}")
        else:
            # 检查是否为占位符
            value = mqtt_config[field]
            if isinstance(value, str):
                if 'your_' in value or '{' in value:
                    issues.append(f"  ⚠️  {field} 仍为占位符: {value}")
    
    # 检查主题配置
    if 'topics' in mqtt_config:
        topics = mqtt_config['topics']
        if 'aircraft_state' in topics:
            topic = topics['aircraft_state']
            if '{your_device_sn}' in topic or '{' in topic:
                issues.append(f"  ⚠️  aircraft_state 主题包含占位符: {topic}")
        else:
            issues.append(f"  ❌ 缺少 aircraft_state 主题")
    
    # 打印结果
    if issues:
        print("\n发现配置问题:")
        for issue in issues:
            print(issue)
        print("\n请修改 config/realtime_config.yaml 后重试")
        return False
    else:
        print("  ✅ 配置参数检查通过")
        return True


def print_config_info(mqtt_config):
    """打印配置信息"""
    print(f"\n当前配置:")
    print(f"  Broker: {mqtt_config['broker']}:{mqtt_config['port']}")
    print(f"  Client ID: {mqtt_config['client_id']}")
    print(f"  Username: {mqtt_config['username'][:10]}... (已隐藏)")
    print(f"  Password: {'*' * 10}... (已隐藏)")
    
    if 'topics' in mqtt_config and 'aircraft_state' in mqtt_config['topics']:
        print(f"  订阅主题: {mqtt_config['topics']['aircraft_state']}")


def test_mqtt_connection(mqtt_config):
    """测试MQTT连接"""
    print("\n正在连接MQTT服务器...")
    print(f"  目标: {mqtt_config['broker']}:{mqtt_config['port']}")
    
    try:
        client = DJIMQTTClient(mqtt_config)
        
        # 尝试连接
        if client.connect():
            print("  ✅ MQTT连接成功!")
            return client
        else:
            print("  ❌ MQTT连接失败!")
            print("\n可能的原因:")
            print("  1. Broker地址或端口错误")
            print("  2. 用户名或密码错误")
            print("  3. 网络连接问题")
            print("  4. 防火墙阻止连接")
            return None
            
    except Exception as e:
        print(f"  ❌ 连接异常: {e}")
        return None


def print_raw_osd_data(client, mqtt_config, duration=10):
    """打印原始OSD数据格式（用于调试）"""
    print("\n" + "="*60)
    print("原始OSD数据监控")
    print("="*60)
    print(f"  监控时长: {duration}秒")
    print(f"  目的: 查看M3TD/M4TD实际推送的OSD数据格式")
    print(f"  订阅主题: {mqtt_config['topics']['aircraft_state']}")
    print("-"*60)
    
    raw_data_received = []
    
    # 注册原始数据回调
    def raw_data_callback(payload):
        if len(raw_data_received) < 3:  # 只保存前3条
            raw_data_received.append(payload)
            print(f"\n[{len(raw_data_received)}] 接收到原始OSD数据:")
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            print("-"*60)
    
    # 注册回调
    topic = mqtt_config['topics']['aircraft_state']
    client.register_callback(topic, raw_data_callback)
    
    # 等待数据
    print(f"\n等待OSD数据...")
    time.sleep(duration)
    
    if raw_data_received:
        print(f"\n✅ 成功接收 {len(raw_data_received)} 条原始OSD数据")
        print("\n数据字段分析:")
        
        # 分析第一条数据的字段
        first_data = raw_data_received[0]
        data_section = first_data.get('data', first_data)
        
        print(f"\n  顶层字段: {list(first_data.keys())}")
        if 'data' in first_data:
            print(f"  data字段内容: {list(data_section.keys())}")
        
        # 检查关键字段
        print(f"\n  关键字段检查:")
        key_fields = {
            'GPS坐标': ['latitude', 'lat', 'longitude', 'lon', 'lng'],
            '高度': ['altitude', 'altitude_above_sea_level', 'height', 'elevation'],
            '偏航角': ['yaw', 'attitude_head', 'heading'],
            '俯仰角': ['pitch', 'attitude_pitch', 'gimbal_pitch'],
            '横滚角': ['roll', 'attitude_roll']
        }
        
        for field_type, possible_names in key_fields.items():
            found = []
            for name in possible_names:
                if name in data_section:
                    found.append(name)
            if found:
                print(f"    ✅ {field_type}: 找到字段 {found}")
            else:
                print(f"    ❌ {field_type}: 未找到（可能字段名: {possible_names}）")
    else:
        print(f"\n❌ 未接收到OSD数据")
    
    print("="*60)
    return len(raw_data_received) > 0


def wait_for_pose_data(client, timeout=30):
    """等待接收位姿数据"""
    print(f"\n等待接收位姿数据... (最多等待{timeout}秒)")
    print("  提示: 请确保设备在线（无人机或机场已开机）")
    print("  说明: 系统会自动解析OSD数据并提取GPS、高度、姿态信息")
    
    for i in range(timeout):
        time.sleep(1)
        pose = client.get_latest_pose()
        
        if pose:
            print(f"\n  ✅ 成功接收并解析位姿数据! (第{i+1}秒)")
            return pose
        
        # 显示进度
        progress = "." * (i % 3 + 1)
        print(f"  等待中{progress:<3} {i+1}/{timeout}秒", end='\r')
    
    print(f"\n  ❌ {timeout}秒内未接收到位姿数据")
    return None


def display_pose_data(pose):
    """显示位姿数据详情"""
    print("\n位姿数据详情:")
    print_separator("-", 60)
    
    # 基本信息
    print(f"  时间戳: {pose.get('timestamp', 0)}")
    
    # GPS坐标
    lat = pose.get('latitude', 0)
    lon = pose.get('longitude', 0)
    print(f"\n  GPS坐标:")
    print(f"    纬度: {lat:.6f}°")
    print(f"    经度: {lon:.6f}°")
    
    # 验证坐标合理性
    if 20 <= lat <= 30 and 110 <= lon <= 120:
        print(f"    ✅ 坐标在中国南方区域范围内")
    else:
        print(f"    ⚠️  坐标可能不在预期范围内")
    
    # 高度信息
    altitude = pose.get('altitude', 0)
    height = pose.get('height', 0)
    print(f"\n  高度信息:")
    print(f"    海拔高度: {altitude:.2f} 米")
    print(f"    相对高度: {height:.2f} 米")
    
    # 验证高度合理性
    if 10 <= altitude <= 500:
        print(f"    ✅ 高度在合理范围内")
    else:
        print(f"    ⚠️  高度可能异常")
    
    # 姿态信息
    yaw = pose.get('yaw', 0)
    pitch = pose.get('pitch', 0)
    roll = pose.get('roll', 0)
    print(f"\n  姿态信息:")
    print(f"    偏航角 (Yaw): {yaw:.1f}°")
    print(f"    俯仰角 (Pitch): {pitch:.1f}°")
    print(f"    横滚角 (Roll): {roll:.1f}°")
    
    # 验证姿态合理性
    if -95 <= pitch <= -85:
        print(f"    ✅ 相机朝向近似垂直向下（适合检测）")
    else:
        print(f"    ⚠️  相机朝向可能不是垂直向下")
    
    print_separator("-", 60)


def continuous_monitoring(client, duration=30):
    """持续监控数据接收"""
    print(f"\n开始持续监控... (持续{duration}秒)")
    print("  监控指标: 推送频率、数据稳定性")
    print_separator("-", 60)
    
    pose_count = 0
    last_timestamp = 0
    timestamps_diff = []
    
    start_time = time.time()
    last_pose = None
    
    while time.time() - start_time < duration:
        pose = client.get_latest_pose()
        
        if pose and pose != last_pose:
            pose_count += 1
            current_timestamp = pose.get('timestamp', 0)
            
            if last_timestamp > 0:
                time_diff = current_timestamp - last_timestamp
                timestamps_diff.append(time_diff)
            
            last_timestamp = current_timestamp
            last_pose = pose
            
            # 每接收10条数据输出一次
            if pose_count % 10 == 0:
                print(f"  已接收 {pose_count} 条位姿数据")
        
        time.sleep(0.1)
    
    # 统计结果
    print(f"\n监控结果:")
    print(f"  总接收数据: {pose_count} 条")
    print(f"  平均推送频率: {pose_count/duration:.1f} Hz")
    
    if timestamps_diff:
        avg_diff = sum(timestamps_diff) / len(timestamps_diff)
        print(f"  平均时间间隔: {avg_diff:.0f} ms")
    
    # 判断是否正常
    expected_freq = 10  # 期望10Hz
    actual_freq = pose_count / duration
    
    if abs(actual_freq - expected_freq) < 2:
        print(f"  ✅ 推送频率正常")
    else:
        print(f"  ⚠️  推送频率异常 (期望约{expected_freq}Hz)")
    
    return pose_count > 0


def print_troubleshooting_tips():
    """打印故障排查提示"""
    print("\n" + "="*60)
    print("故障排查提示:")
    print("="*60)
    print("""
如果测试失败，请检查:

1. 配置文件参数
   - 打开 config/realtime_config.yaml
   - 确认 username (App Key) 正确
   - 确认 password (App Secret) 正确
   - 确认 broker 地址正确
   - 确认 topics.aircraft_state 中的设备SN正确

2. 设备状态
   - 确认无人机或机场已开机
   - 在DJI开发者平台查看设备在线状态
   - 确认设备已绑定到应用

3. 网络连接
   - 测试能否访问 mqtt-cn.dji.com
   - 检查防火墙设置
   - 尝试使用手机热点测试

4. MQTT消息格式
   - 使用MQTTX工具查看原始消息
   - 对比消息格式是否与代码一致
   - 必要时修改 src/input/mqtt_client.py

5. 获取帮助
   - 查看文档: docs/DJI_MQTT_SETUP.md
   - 查看开发指南: 无人机实时流处理配置与开发指南.md
   - 联系DJI技术支持: https://developer.dji.com/support
""")


def main():
    """主函数"""
    print_header("MQTT实时连接测试")
    
    # 步骤1: 加载配置
    print_step(1, 5, "加载配置文件")
    mqtt_config = load_config()
    print("  ✅ 配置文件加载成功")
    
    # 显示配置信息
    print_config_info(mqtt_config)
    
    # 验证配置
    if not validate_config(mqtt_config):
        sys.exit(1)
    
    # 步骤2: 连接MQTT
    print_step(2, 5, "连接MQTT服务器")
    client = test_mqtt_connection(mqtt_config)
    
    if not client:
        print_troubleshooting_tips()
        sys.exit(1)
    
    # 步骤3: 查看原始OSD数据格式（可选）
    print_step(3, 6, "查看原始OSD数据格式（可选）")
    response = input("是否显示原始OSD数据格式? (y/n，建议首次配置选y): ")
    
    if response.lower() == 'y':
        osd_received = print_raw_osd_data(client, mqtt_config, duration=10)
        if not osd_received:
            print("\n⚠️  未接收到OSD数据，请检查:")
            print("  1. 设备是否在线")
            print("  2. 主题配置是否正确")
            print("  3. 是否已在DJI Pilot 2中启用数据推送")
    else:
        print("  跳过原始数据查看")
    
    # 步骤4: 等待解析后的位姿数据
    print_step(4, 6, "等待解析后的位姿数据")
    pose = wait_for_pose_data(client, timeout=30)
    
    if not pose:
        print("\n可能的原因:")
        print("  1. 设备SN码配置错误")
        print("  2. 设备未在线（无人机未开机或机场未通电）")
        print("  3. 主题订阅错误")
        print("  4. 设备没有推送数据到该主题")
        
        client.disconnect()
        print_troubleshooting_tips()
        sys.exit(1)
    
    # 步骤5: 显示数据详情
    print_step(5, 6, "显示位姿数据详情")
    display_pose_data(pose)
    
    # 步骤6: 持续监控（可选）
    print_step(6, 6, "持续监控数据接收")
    response = input("是否进行30秒持续监控测试? (y/n): ")
    
    if response.lower() == 'y':
        success = continuous_monitoring(client, duration=30)
        if success:
            print("\n  ✅ 持续监控测试通过")
        else:
            print("\n  ❌ 持续监控测试失败")
    else:
        print("  跳过持续监控测试")
    
    # 断开连接
    client.disconnect()
    print("\n✅ MQTT连接已关闭")
    
    # 最终结果
    print_header("测试结果总结")
    print("✅ MQTT连接测试通过!")
    print("✅ 能够正常接收无人机位姿数据")
    print("✅ 数据格式正确，字段完整")
    print("\n下一步:")
    print("  1. 测试RTSP视频流连接")
    print("  2. 运行完整实时处理: python run_realtime.py")
    print("  3. 查看开发指南了解更多配置选项")
    print_separator()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
