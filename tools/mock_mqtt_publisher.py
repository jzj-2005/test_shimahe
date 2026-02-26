"""
Mock MQTT 发布者
模拟 DJI M3TD/M4TD 无人机通过 MQTT 推送 OSD 位姿数据。

前置条件:
    1. 安装本地 MQTT Broker (Mosquitto):
       Windows: winget install EclipseFoundation.Mosquitto
       或从 https://mosquitto.org/download/ 下载
    2. 确保 Mosquitto 已启动，默认监听 localhost:1883

用法:
    # 默认参数启动（localhost:1883，10Hz推送）
    python tools/mock_mqtt_publisher.py

    # 自定义参数
    python tools/mock_mqtt_publisher.py --broker localhost --port 1883 --hz 10 --duration 60

    # 指定飞行轨迹起点
    python tools/mock_mqtt_publisher.py --lat 22.78 --lon 114.10 --alt 120

配合使用:
    1. 修改 config/realtime_config.yaml (或使用 config/simulation_config.yaml):
       mqtt.broker: "localhost"
       mqtt.username: ""
       mqtt.password: ""
       mqtt.topics.aircraft_state: "thing/product/MOCK_DEVICE_SN/osd"
    2. 启动本脚本
    3. 启动实时管道: python src/main.py --mode realtime
"""

import json
import time
import math
import random
import argparse
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("缺少 paho-mqtt 库，请安装: pip install paho-mqtt")
    exit(1)


MOCK_DEVICE_SN = "MOCK_DEVICE_SN"


class FlightSimulator:
    """模拟无人机飞行轨迹"""

    def __init__(self, start_lat: float, start_lon: float, altitude: float,
                 speed: float = 5.0, pattern: str = "circle"):
        self.lat = start_lat
        self.lon = start_lon
        self.altitude = altitude
        self.speed = speed
        self.pattern = pattern

        self.time_elapsed = 0.0
        self.meters_per_deg_lat = 110540.0
        self.meters_per_deg_lon = 111320.0 * math.cos(math.radians(start_lat))

        # 圆形轨迹参数
        self.circle_radius = 200.0  # 米
        self.center_lat = start_lat
        self.center_lon = start_lon

    def update(self, dt: float) -> dict:
        """更新位置并返回 OSD payload"""
        self.time_elapsed += dt

        if self.pattern == "circle":
            angle = self.time_elapsed * self.speed / self.circle_radius
            dx = self.circle_radius * math.cos(angle)
            dy = self.circle_radius * math.sin(angle)
            self.lat = self.center_lat + dy / self.meters_per_deg_lat
            self.lon = self.center_lon + dx / self.meters_per_deg_lon
            yaw = math.degrees(angle + math.pi / 2) % 360
        elif self.pattern == "line":
            heading = math.radians(45)
            dist = self.speed * self.time_elapsed
            self.lat = self.center_lat + dist * math.cos(heading) / self.meters_per_deg_lat
            self.lon = self.center_lon + dist * math.sin(heading) / self.meters_per_deg_lon
            yaw = 45.0
        else:
            yaw = 0.0

        alt_jitter = random.uniform(-0.5, 0.5)

        payload = {
            "tid": "mock_tid_001",
            "bid": "mock_bid_001",
            "timestamp": int(time.time() * 1000),
            "data": {
                "latitude": round(self.lat, 8),
                "longitude": round(self.lon, 8),
                "altitude": round(self.altitude + alt_jitter, 2),
                "height": round(self.altitude - 30 + alt_jitter, 2),
                "attitude_head": round(yaw, 2),
                "attitude_pitch": round(-89.5 + random.uniform(-0.5, 0.5), 2),
                "attitude_roll": round(random.uniform(-0.5, 0.5), 2),
                "gimbal_pitch": -90.0,
                "speed": round(self.speed + random.uniform(-0.3, 0.3), 2),
                "battery_percent": max(10, 100 - int(self.time_elapsed / 10)),
                "gps_level": 5,
                "satellite_count": random.randint(14, 22),
            }
        }
        return payload


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"  [OK] 已连接到 MQTT Broker")
    else:
        print(f"  [FAIL] 连接失败，返回码: {rc}")


def main():
    parser = argparse.ArgumentParser(description='Mock MQTT 位姿数据发布者')
    parser.add_argument('--broker', type=str, default='localhost',
                        help='MQTT Broker 地址 (默认: localhost)')
    parser.add_argument('--port', type=int, default=1883,
                        help='MQTT 端口 (默认: 1883)')
    parser.add_argument('--hz', type=float, default=10.0,
                        help='推送频率 Hz (默认: 10)')
    parser.add_argument('--duration', type=float, default=0,
                        help='持续时间/秒 (0=无限, 默认: 0)')
    parser.add_argument('--lat', type=float, default=22.779954,
                        help='起始纬度 (默认: 22.779954)')
    parser.add_argument('--lon', type=float, default=114.100891,
                        help='起始经度 (默认: 114.100891)')
    parser.add_argument('--alt', type=float, default=120.0,
                        help='飞行高度/米 (默认: 120)')
    parser.add_argument('--speed', type=float, default=5.0,
                        help='飞行速度 m/s (默认: 5.0)')
    parser.add_argument('--pattern', type=str, default='circle',
                        choices=['circle', 'line'],
                        help='飞行轨迹: circle(绕圈) 或 line(直线)')
    parser.add_argument('--device-sn', type=str, default=MOCK_DEVICE_SN,
                        help=f'模拟设备SN (默认: {MOCK_DEVICE_SN})')
    args = parser.parse_args()

    topic = f"thing/product/{args.device_sn}/osd"
    interval = 1.0 / args.hz

    print("=" * 60)
    print("  Mock MQTT 发布者 (模拟 DJI OSD)")
    print("=" * 60)
    print(f"  Broker:   {args.broker}:{args.port}")
    print(f"  Topic:    {topic}")
    print(f"  频率:     {args.hz} Hz")
    print(f"  轨迹:     {args.pattern}")
    print(f"  起始GPS:  ({args.lat}, {args.lon})")
    print(f"  高度:     {args.alt} m")
    print(f"  持续:     {'无限' if args.duration == 0 else f'{args.duration}秒'}")
    print("-" * 60)

    # 连接 MQTT
    client = mqtt.Client(client_id=f"mock_publisher_{int(time.time())}")
    client.on_connect = on_connect

    try:
        client.connect(args.broker, args.port, keepalive=60)
        client.loop_start()
    except Exception as e:
        print(f"\n  [FAIL] 无法连接到 {args.broker}:{args.port}")
        print(f"         错误: {e}")
        print(f"\n  请确认 Mosquitto 已启动:")
        print(f"    Windows: net start mosquitto")
        print(f"    或手动启动: mosquitto -v")
        return

    time.sleep(1)

    sim = FlightSimulator(
        start_lat=args.lat,
        start_lon=args.lon,
        altitude=args.alt,
        speed=args.speed,
        pattern=args.pattern,
    )

    msg_count = 0
    start_time = time.time()

    print(f"\n  开始推送... (Ctrl+C 停止)\n")

    try:
        while True:
            payload = sim.update(interval)
            msg_json = json.dumps(payload, ensure_ascii=False)
            client.publish(topic, msg_json, qos=1)
            msg_count += 1

            data = payload['data']
            if msg_count % int(args.hz) == 0:
                elapsed = time.time() - start_time
                print(f"  [{elapsed:>6.1f}s] 已发送 {msg_count:>5d} 条 | "
                      f"GPS ({data['latitude']:.6f}, {data['longitude']:.6f}) | "
                      f"高度 {data['altitude']:.1f}m | "
                      f"航向 {data['attitude_head']:.1f}")

            if args.duration > 0 and (time.time() - start_time) >= args.duration:
                print(f"\n  已达到设定时长 {args.duration}s，停止推送")
                break

            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n\n  用户中断")

    elapsed_total = time.time() - start_time
    print(f"\n  总计发送: {msg_count} 条消息, 耗时 {elapsed_total:.1f}s")
    print(f"  实际频率: {msg_count / elapsed_total:.1f} Hz")

    client.loop_stop()
    client.disconnect()
    print("  MQTT 连接已断开")
    print("=" * 60)


if __name__ == '__main__':
    main()
