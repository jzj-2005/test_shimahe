"""
DJI MQTT连接测试脚本
用于验证MQTT配置是否正确
"""

import sys
import time
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.input.mqtt_client import DJIMQTTClient
from src.utils.config_loader import ConfigLoader


def test_mqtt_connection():
    """测试MQTT连接"""
    print("="*60)
    print("DJI MQTT连接测试")
    print("="*60)
    
    # 加载配置
    print("\n步骤1: 加载配置文件...")
    try:
        config_loader = ConfigLoader('./config')
        realtime_config = config_loader.load('realtime_config')
        mqtt_config = realtime_config.get('mqtt', {})
        
        print(f"✓ 配置加载成功")
        print(f"  服务器: {mqtt_config.get('broker')}:{mqtt_config.get('port')}")
        print(f"  用户名: {mqtt_config.get('username')}")
        print(f"  客户端ID: {mqtt_config.get('client_id')}")
    except Exception as e:
        print(f"✗ 配置加载失败: {e}")
        return
    
    # 检查配置是否为默认值
    if mqtt_config.get('username') == 'your_username':
        print("\n⚠️  警告: 检测到默认配置值")
        print("   请先在 config/realtime_config.yaml 中配置实际的MQTT参数")
        print("\n需要配置的参数:")
        print("  1. broker: MQTT服务器地址（mqtt-cn.dji.com 或 mqtt-us.dji.com）")
        print("  2. username: 你的App Key")
        print("  3. password: 你的App Secret")
        print("  4. topics.aircraft_state: 设备主题（包含实际设备SN）")
        return
    
    # 创建MQTT客户端
    print("\n步骤2: 创建MQTT客户端...")
    try:
        client = DJIMQTTClient(
            broker=mqtt_config.get('broker'),
            port=mqtt_config.get('port', 1883),
            username=mqtt_config.get('username', ''),
            password=mqtt_config.get('password', ''),
            client_id=mqtt_config.get('client_id', 'test_client'),
            topics=mqtt_config.get('topics', {}),
            qos=mqtt_config.get('qos', 1),
            keep_alive=mqtt_config.get('keep_alive', 60),
            pose_buffer_size=mqtt_config.get('pose_buffer_size', 100)
        )
        print("✓ 客户端创建成功")
    except Exception as e:
        print(f"✗ 客户端创建失败: {e}")
        return
    
    # 尝试连接
    print("\n步骤3: 连接MQTT服务器...")
    try:
        if client.connect(timeout=15):
            print("✓ MQTT连接成功!")
            
            # 等待接收数据
            print("\n步骤4: 等待接收位姿数据...")
            print("提示: 请确保设备在线（机场通电、无人机开机）")
            print("等待15秒...")
            
            for i in range(15):
                time.sleep(1)
                print(".", end="", flush=True)
                
                # 每3秒检查一次
                if (i + 1) % 3 == 0:
                    pose = client.get_latest_pose()
                    if pose:
                        print(f"\n✓ 成功接收到位姿数据!")
                        break
            
            print()
            
            # 检查最终结果
            pose = client.get_latest_pose()
            
            if pose:
                print("\n=== 接收到的数据 ===")
                print(f"时间戳: {pose.get('timestamp', 0):.0f} ms")
                
                if 'latitude' in pose and 'longitude' in pose:
                    print(f"GPS坐标: ({pose['latitude']:.6f}, {pose['longitude']:.6f})")
                else:
                    print("GPS坐标: 无")
                
                if 'altitude' in pose:
                    print(f"飞行高度: {pose['altitude']:.1f} m")
                else:
                    print("飞行高度: 无")
                
                if 'yaw' in pose:
                    print(f"偏航角: {pose['yaw']:.1f}°")
                if 'pitch' in pose:
                    print(f"俯仰角: {pose['pitch']:.1f}°")
                if 'roll' in pose:
                    print(f"横滚角: {pose['roll']:.1f}°")
                
                print("\n✓ MQTT连接测试成功!")
                print("  可以开始使用实时模式了")
            else:
                print("\n⚠️  连接成功但未接收到数据")
                print("\n可能的原因:")
                print("  1. 设备未在线（检查机场/无人机是否开机）")
                print("  2. 主题订阅错误（检查设备SN是否正确）")
                print("  3. 设备未推送数据（检查设备状态）")
                print("\n建议:")
                print("  1. 确认设备在线状态")
                print("  2. 检查 config/realtime_config.yaml 中的设备SN")
                print("  3. 使用MQTT客户端工具（如MQTTX）验证数据推送")
            
            # 打印统计信息
            print("\n=== MQTT统计信息 ===")
            client.print_stats()
            
            # 断开连接
            client.disconnect()
            
        else:
            print("✗ MQTT连接失败")
            print("\n可能的原因:")
            print("  1. 网络无法访问MQTT服务器")
            print("  2. 用户名或密码错误（App Key/Secret）")
            print("  3. 服务器地址或端口错误")
            print("\n建议:")
            print("  1. 检查网络连接，ping mqtt-cn.dji.com")
            print("  2. 验证DJI开发者平台的App Key和App Secret")
            print("  3. 确认服务器地址正确（中国用mqtt-cn.dji.com）")
            
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        client.disconnect()
    except Exception as e:
        print(f"\n✗ 连接过程发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)


def print_help():
    """打印帮助信息"""
    print("""
配置步骤:
    
1. 注册DJI开发者账号
   访问: https://developer.dji.com/
   
2. 创建应用获取凭证
   - 登录开发者平台
   - 创建云服务应用
   - 获取 App Key 和 App Secret
   
3. 绑定设备
   - 在应用中添加设备
   - 记录设备SN码
   
4. 修改配置文件
   编辑: config/realtime_config.yaml
   
   mqtt:
     broker: "mqtt-cn.dji.com"              # 中国大陆使用
     port: 1883
     username: "your_app_key"               # 替换为实际App Key
     password: "your_app_secret"            # 替换为实际App Secret
     client_id: "your_app_id"
     topics:
       aircraft_state: "thing/product/YOUR_DEVICE_SN/state"  # 替换设备SN
   
5. 运行测试
   python test_mqtt_connection.py

详细文档请查看: docs/DJI_MQTT_SETUP.md
    """)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print_help()
    else:
        test_mqtt_connection()
