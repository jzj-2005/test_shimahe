# DJI Cloud API MQTT 配置指南

## 概述

DJI Cloud API使用MQTT协议进行无人机与云端的实时通信。本指南将帮助你完成MQTT连接配置。

## 一、准备工作

### 1. 注册DJI开发者账号

访问：https://developer.dji.com/

1. 点击"注册"创建账号
2. 完成邮箱验证
3. 登录开发者平台

### 2. 创建应用获取凭证

1. 登录后进入"控制台"
2. 点击"创建应用"
3. 填写应用信息：
   - 应用名称：例如"水利巡检系统"
   - 应用类型：选择"云服务应用"
   - 应用描述：简要说明用途
4. 创建成功后，记录以下信息：
   - **App ID** (应用标识)
   - **App Key** (应用密钥)
   - **App License** (应用许可)

### 3. 绑定设备

1. 在应用详情页面，找到"设备管理"
2. 添加你的DJI设备（机场或无人机）
3. 记录设备的 **SN码** (序列号)

## 二、MQTT连接参数说明

### 基本参数

| 参数 | 说明 | 示例值 |
|------|------|--------|
| broker | MQTT服务器地址 | mqtt-cn.dji.com 或 mqtt-us.dji.com |
| port | 端口号 | 1883 (TCP) 或 8883 (SSL) |
| username | 用户名 | 你的App Key |
| password | 密码 | 通过App Key和App Secret计算得出 |
| client_id | 客户端ID | 自定义，建议使用App ID |

### 服务器地址选择

- **中国大陆**: `mqtt-cn.dji.com`
- **其他地区**: `mqtt-us.dji.com`

### 认证方式

DJI Cloud API支持两种认证方式：

#### 方式1：使用App Key直接认证（推荐）

```yaml
mqtt:
  broker: "mqtt-cn.dji.com"
  port: 1883
  username: "your_app_key"        # 直接使用App Key
  password: "your_app_secret"     # 直接使用App Secret
  client_id: "your_app_id"        # 使用App ID
```

#### 方式2：使用签名认证（更安全）

需要根据DJI文档生成签名token作为密码。

## 三、MQTT主题订阅

### 主题格式

DJI Cloud API的MQTT主题格式：

```
thing/product/{gateway_sn}/{sub_topic}
```

- `{gateway_sn}`: 设备序列号（机场或无人机SN码）
- `{sub_topic}`: 具体功能主题

### 常用主题

#### 1. 无人机状态数据（重要）

```yaml
topics:
  # 无人机状态主题 - 包含GPS、高度、姿态等
  aircraft_state: "thing/product/{gateway_sn}/state"
```

**数据示例**：
```json
{
  "tid": "xxxxxxxx",
  "bid": "xxxxxxxx",
  "timestamp": 1234567890,
  "data": {
    "latitude": 31.234567,
    "longitude": 121.456789,
    "altitude": 120.5,
    "height": 100.0,
    "attitude": {
      "yaw": 45.2,
      "pitch": -90.0,
      "roll": 0.1
    },
    "speed": {
      "horizontal": 5.2,
      "vertical": 0.0
    }
  }
}
```

#### 2. 设备在线状态

```yaml
topics:
  device_online: "thing/product/{gateway_sn}/online"
```

#### 3. 设备属性上报

```yaml
topics:
  device_property: "thing/product/{gateway_sn}/property/get"
```

#### 4. 设备事件上报

```yaml
topics:
  device_events: "thing/product/{gateway_sn}/events"
```

### 完整配置示例

```yaml
mqtt:
  broker: "mqtt-cn.dji.com"
  port: 1883
  username: "abcdef1234567890"           # 替换为你的App Key
  password: "your_app_secret_here"       # 替换为你的App Secret
  client_id: "inspection_app_001"        # 替换为你的App ID或自定义
  
  topics:
    # 主要订阅主题 - 无人机状态
    aircraft_state: "thing/product/1581F5BKD2332000ABCD/state"  # 替换设备SN
    
    # 可选订阅主题
    device_online: "thing/product/1581F5BKD2332000ABCD/online"
    device_events: "thing/product/1581F5BKD2332000ABCD/events"
  
  qos: 1              # QoS级别：0=最多一次, 1=至少一次, 2=只有一次
  keep_alive: 60      # 心跳间隔(秒)
  connection_timeout: 10
  reconnect_interval: 5
  pose_buffer_size: 100
```

## 四、获取设备SN码

### 方法1：从DJI Pilot查看

1. 连接无人机
2. 打开DJI Pilot App
3. 进入设置 → 关于 → 查看序列号

### 方法2：从机场查看

1. 登录机场控制台
2. 系统信息 → 设备序列号

### 方法3：从DJI开发者平台查看

1. 登录开发者平台
2. 应用管理 → 设备管理
3. 查看已绑定设备的SN码

## 五、配置实例

### 示例1：M3TD无人机 + 机场

```yaml
mqtt:
  broker: "mqtt-cn.dji.com"
  port: 1883
  
  # 认证信息（从DJI开发者平台获取）
  username: "1234567890abcdef1234567890abcdef"  # App Key
  password: "abcdefghijklmnopqrstuvwxyz123456"  # App Secret
  client_id: "water_inspection_app_v1"          # App ID或自定义
  
  # 订阅主题（使用实际设备SN）
  topics:
    aircraft_state: "thing/product/1581F5BKD233200012AB/state"
    device_online: "thing/product/1581F5BKD233200012AB/online"
  
  qos: 1
  keep_alive: 60
  connection_timeout: 10
  reconnect_interval: 5
  pose_buffer_size: 100
```

## 六、测试连接

### 方法1：使用Python测试脚本

创建测试文件 `test_mqtt_connection.py`：

```python
import sys
sys.path.insert(0, './')

from src.input.mqtt_client import DJIMQTTClient
import time

# 配置参数
mqtt_config = {
    'broker': 'mqtt-cn.dji.com',
    'port': 1883,
    'username': 'your_app_key',           # 替换
    'password': 'your_app_secret',        # 替换
    'client_id': 'test_client',
    'topics': {
        'aircraft_state': 'thing/product/YOUR_DEVICE_SN/state'  # 替换
    },
    'qos': 1,
    'keep_alive': 60
}

# 创建客户端
client = DJIMQTTClient(**mqtt_config)

# 测试连接
print("正在连接MQTT服务器...")
if client.connect():
    print("✓ MQTT连接成功!")
    
    # 等待接收数据
    print("等待接收位姿数据...")
    time.sleep(10)
    
    # 检查数据
    pose = client.get_latest_pose()
    if pose:
        print(f"✓ 成功接收位姿数据:")
        print(f"  GPS: ({pose.get('latitude', 0):.6f}, {pose.get('longitude', 0):.6f})")
        print(f"  高度: {pose.get('altitude', 0):.1f}m")
    else:
        print("✗ 未接收到位姿数据")
    
    client.disconnect()
else:
    print("✗ MQTT连接失败")
```

运行测试：
```bash
python test_mqtt_connection.py
```

### 方法2：使用MQTT客户端工具

推荐工具：**MQTT Explorer** 或 **MQTTX**

1. 下载安装工具
2. 创建新连接：
   - Host: `mqtt-cn.dji.com`
   - Port: `1883`
   - Username: 你的App Key
   - Password: 你的App Secret
3. 连接成功后订阅主题：`thing/product/{你的设备SN}/state`
4. 观察是否收到数据

## 七、常见问题

### Q1: 连接失败，返回码5（认证失败）

**原因**：用户名或密码错误

**解决**：
1. 检查App Key和App Secret是否正确
2. 确认没有多余的空格或换行
3. 验证设备是否已绑定到应用

### Q2: 连接成功但收不到数据

**原因**：主题订阅错误或设备未在线

**解决**：
1. 检查设备SN码是否正确
2. 确认设备在线（机场通电、无人机开机）
3. 使用通配符订阅测试：`thing/product/+/state`

### Q3: 如何获取M3D的属性数据？

参考你提供的文档：
https://developer.dji.com/doc/cloud-api-tutorial/cn/api-reference/dock-to-cloud/mqtt/aircraft/m3d-properties.html

主题格式：
```
thing/product/{gateway_sn}/osd
```

### Q4: 端口1883和8883的区别

- **1883**: 标准MQTT端口（TCP明文传输）
- **8883**: MQTT over SSL/TLS（加密传输，更安全）

生产环境建议使用8883端口。

## 八、数据字段映射

### 位姿数据映射关系

| 字段路径 | 说明 | 代码中的键名 |
|---------|------|-------------|
| data.latitude | 纬度 | latitude |
| data.longitude | 经度 | longitude |
| data.altitude | 海拔高度(m) | altitude |
| data.height | 相对高度(m) | height |
| data.attitude.yaw | 偏航角(度) | yaw |
| data.attitude.pitch | 俯仰角(度) | pitch |
| data.attitude.roll | 横滚角(度) | roll |

### 代码中的数据处理

位置：`src/input/mqtt_client.py` 的 `_handle_aircraft_state` 方法

```python
def _handle_aircraft_state(self, payload):
    """处理无人机状态消息"""
    pose = {
        'timestamp': time.time() * 1000,
        'latitude': float(payload['data']['latitude']),
        'longitude': float(payload['data']['longitude']),
        'altitude': float(payload['data']['altitude']),
        'yaw': float(payload['data']['attitude']['yaw']),
        'pitch': float(payload['data']['attitude']['pitch']),
        'roll': float(payload['data']['attitude']['roll'])
    }
    # 添加到缓冲区...
```

如果DJI的实际数据格式不同，需要修改这个方法。

## 九、配置检查清单

在运行实时模式前，请确认：

- [ ] 已注册DJI开发者账号
- [ ] 已创建应用并获取App Key和App Secret
- [ ] 已绑定设备并记录SN码
- [ ] 已更新 `config/realtime_config.yaml` 中的MQTT配置
- [ ] 已替换占位符（username、password、device SN）
- [ ] 设备在线（机场通电、无人机开机）
- [ ] 网络可访问 mqtt-cn.dji.com
- [ ] 已测试MQTT连接成功

## 十、参考资源

- DJI开发者文档: https://developer.dji.com/doc/cloud-api-tutorial/cn/
- MQTT协议说明: https://mqtt.org/
- M3D属性文档: https://developer.dji.com/doc/cloud-api-tutorial/cn/api-reference/dock-to-cloud/mqtt/aircraft/m3d-properties.html

---

**配置完成后，使用以下命令测试**：

```bash
python run_realtime.py
```

如果连接成功，你将看到：
```
MQTT连接成功
已订阅主题: aircraft_state -> thing/product/YOUR_SN/state
```
