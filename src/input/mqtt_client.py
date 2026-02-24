"""
MQTT客户端
用于连接DJI Cloud API，接收无人机实时位姿数据
"""

import json
import time
import threading
from typing import Dict, Any, Optional, Callable
from collections import deque
import paho.mqtt.client as mqtt
from loguru import logger


class DJIMQTTClient:
    """DJI MQTT客户端类"""
    
    def __init__(
        self,
        broker: str,
        port: int = 1883,
        username: str = "",
        password: str = "",
        client_id: str = "drone_inspection_client",
        topics: Dict[str, str] = None,
        qos: int = 1,
        keep_alive: int = 60,
        pose_buffer_size: int = 100
    ):
        """
        初始化MQTT客户端
        
        Args:
            broker: MQTT服务器地址
            port: 端口
            username: 用户名
            password: 密码
            client_id: 客户端ID
            topics: 订阅主题字典
            qos: QoS级别
            keep_alive: 保持连接时间 (秒)
            pose_buffer_size: 位姿数据缓冲区大小
        """
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id
        self.topics = topics or {}
        self.qos = qos
        self.keep_alive = keep_alive
        
        # MQTT客户端
        self.client = mqtt.Client(client_id=client_id)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # 设置用户名和密码
        if username and password:
            self.client.username_pw_set(username, password)
        
        # 连接状态
        self.is_connected = False
        self.reconnect_interval = 5
        
        # 位姿数据缓冲区
        self.pose_buffer = deque(maxlen=pose_buffer_size)
        self.buffer_lock = threading.Lock()
        
        # 最新位姿数据
        self.latest_pose = None
        
        # 统计信息
        self.message_count = 0
        self.last_message_time = 0
        
        # 自定义回调函数
        self.custom_callbacks = {}
    
    def connect(self, timeout: int = 10) -> bool:
        """
        连接到MQTT服务器
        
        Args:
            timeout: 连接超时 (秒)
            
        Returns:
            是否成功连接
        """
        try:
            logger.info(f"正在连接到MQTT服务器: {self.broker}:{self.port}")
            
            self.client.connect(self.broker, self.port, self.keep_alive)
            self.client.loop_start()
            
            # 等待连接成功
            start_time = time.time()
            while not self.is_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self.is_connected:
                logger.info("MQTT连接成功")
                return True
            else:
                logger.error("MQTT连接超时")
                return False
                
        except Exception as e:
            logger.error(f"连接MQTT服务器时发生错误: {e}")
            return False
    
    def disconnect(self):
        """断开MQTT连接"""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT连接已断开")
        except Exception as e:
            logger.error(f"断开MQTT连接时发生错误: {e}")
    
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            self.is_connected = True
            logger.info("MQTT连接建立成功")
            
            # 订阅主题
            self._subscribe_topics()
        else:
            self.is_connected = False
            logger.error(f"MQTT连接失败，返回码: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        self.is_connected = False
        
        if rc != 0:
            logger.warning(f"MQTT连接意外断开，返回码: {rc}")
            logger.info(f"{self.reconnect_interval}秒后尝试重连...")
        else:
            logger.info("MQTT连接正常断开")
    
    def _on_message(self, client, userdata, msg):
        """消息接收回调"""
        try:
            # 解析JSON消息
            payload = json.loads(msg.payload.decode('utf-8'))
            
            # 更新统计信息
            self.message_count += 1
            self.last_message_time = time.time()
            
            # 处理消息
            topic = msg.topic
            
            # 如果是无人机状态主题
            if 'aircraft_state' in self.topics and topic == self.topics['aircraft_state']:
                self._handle_aircraft_state(payload)
            
            # 调用自定义回调
            if topic in self.custom_callbacks:
                self.custom_callbacks[topic](payload)
            
            logger.debug(f"收到MQTT消息: {topic}")
            
        except json.JSONDecodeError as e:
            logger.error(f"解析MQTT消息失败: {e}")
        except Exception as e:
            logger.error(f"处理MQTT消息时发生错误: {e}")
    
    def _subscribe_topics(self):
        """订阅所有配置的主题"""
        for name, topic in self.topics.items():
            try:
                self.client.subscribe(topic, qos=self.qos)
                logger.info(f"已订阅主题: {name} -> {topic}")
            except Exception as e:
                logger.error(f"订阅主题失败 {topic}: {e}")
    
    def _handle_aircraft_state(self, payload: Dict[str, Any]):
        """
        处理无人机OSD消息（支持M3TD/M4TD）
        
        Args:
            payload: 消息载荷
            
        OSD数据格式示例:
        {
            "tid": "xxx",
            "bid": "xxx",
            "timestamp": 1707730815123,
            "data": {
                "latitude": 22.779954,
                "longitude": 114.100891,
                "altitude": 139.231,  # 或 altitude_above_sea_level
                "height": 120.5,
                "attitude_head": 45.2,  # 或 yaw
                "attitude_pitch": -88.5,  # 或 pitch
                "attitude_roll": 0.1,  # 或 roll
                "gimbal_pitch": -90.0
            }
        }
        """
        try:
            # 提取data字段（OSD数据通常在data字段中）
            # 如果没有data字段，则使用整个payload
            data = payload.get('data', payload)
            
            # 提取时间戳
            # 优先使用payload中的timestamp，如果没有则使用当前时间
            pose = {
                'timestamp': payload.get('timestamp', time.time() * 1000),
            }
            
            # ========== 提取GPS坐标 ==========
            # 支持多种可能的字段名称
            pose['latitude'] = float(
                data.get('latitude') or           # 标准字段名
                data.get('lat') or                # 简写
                data.get('position_lat') or       # 嵌套字段
                data.get('gps_lat') or            # GPS前缀
                0
            )
            
            pose['longitude'] = float(
                data.get('longitude') or          # 标准字段名
                data.get('lon') or                # 简写
                data.get('lng') or                # 另一种简写
                data.get('position_lon') or       # 嵌套字段
                data.get('position_lng') or
                data.get('gps_lon') or            # GPS前缀
                data.get('gps_lng') or
                0
            )
            
            # ========== 提取高度 ==========
            # 支持多种可能的字段名称
            # 优先使用海拔高度，其次是相对高度
            pose['altitude'] = float(
                data.get('altitude') or                    # 标准字段名
                data.get('altitude_above_sea_level') or    # DJI完整字段名
                data.get('altitude_asl') or                # 简写
                data.get('height') or                      # 相对高度
                data.get('relative_height') or             # 相对高度完整名
                data.get('elevation') or                   # 海拔
                0
            )
            
            # 如果altitude为0但有height，使用height
            if pose['altitude'] == 0 and 'height' in data:
                pose['altitude'] = float(data['height'])
            
            # ========== 提取姿态角 ==========
            
            # 偏航角（航向角）
            pose['yaw'] = float(
                data.get('yaw') or                  # 标准字段名
                data.get('attitude_head') or        # DJI字段名
                data.get('heading') or              # 航向
                data.get('compass_heading') or      # 罗盘航向
                0
            )
            
            # 俯仰角
            pose['pitch'] = float(
                data.get('pitch') or                # 标准字段名
                data.get('attitude_pitch') or       # DJI字段名
                data.get('gimbal_pitch') or         # 云台俯仰（备用）
                -90  # 默认值：垂直向下
            )
            
            # 横滚角
            pose['roll'] = float(
                data.get('roll') or                 # 标准字段名
                data.get('attitude_roll') or        # DJI字段名
                0
            )
            
            # ========== 数据验证 ==========
            # 检查关键数据是否有效
            if pose['latitude'] == 0 or pose['longitude'] == 0:
                logger.warning("接收到的GPS坐标为0，可能数据无效")
                logger.debug(f"原始数据: {data}")
                
            if pose['altitude'] == 0:
                logger.warning("接收到的高度为0，可能数据无效")
            
            # 检查GPS坐标是否在合理范围内（中国范围：纬度18-54，经度73-135）
            if not (18 <= pose['latitude'] <= 54):
                logger.warning(f"纬度超出合理范围: {pose['latitude']}")
            if not (73 <= pose['longitude'] <= 135):
                logger.warning(f"经度超出合理范围: {pose['longitude']}")
            
            # ========== 添加到缓冲区 ==========
            with self.buffer_lock:
                self.pose_buffer.append(pose)
                self.latest_pose = pose
            
            logger.debug(f"[OSD] 接收位姿数据: GPS({pose['latitude']:.6f}, "
                        f"{pose['longitude']:.6f}), 高度{pose['altitude']:.1f}m, "
                        f"姿态(yaw={pose['yaw']:.1f}°, pitch={pose['pitch']:.1f}°)")
            
        except Exception as e:
            logger.error(f"处理OSD数据时发生错误: {e}")
            logger.debug(f"错误详情 - 原始payload: {payload}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def get_latest_pose(self) -> Optional[Dict[str, Any]]:
        """
        获取最新的位姿数据
        
        Returns:
            最新位姿数据，如果没有则返回None
        """
        with self.buffer_lock:
            return self.latest_pose.copy() if self.latest_pose else None
    
    def get_pose_buffer(self) -> list:
        """
        获取位姿数据缓冲区的副本
        
        Returns:
            位姿数据列表
        """
        with self.buffer_lock:
            return list(self.pose_buffer)
    
    def clear_buffer(self):
        """清空位姿数据缓冲区"""
        with self.buffer_lock:
            self.pose_buffer.clear()
            self.latest_pose = None
        logger.info("MQTT位姿数据缓冲区已清空")
    
    def register_callback(self, topic: str, callback: Callable[[Dict[str, Any]], None]):
        """
        注册自定义主题回调函数
        
        Args:
            topic: 主题
            callback: 回调函数，接收消息载荷作为参数
        """
        self.custom_callbacks[topic] = callback
        logger.info(f"已注册主题回调: {topic}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        time_since_last = time.time() - self.last_message_time if self.last_message_time > 0 else 0
        
        with self.buffer_lock:
            buffer_size = len(self.pose_buffer)
        
        return {
            'is_connected': self.is_connected,
            'message_count': self.message_count,
            'buffer_size': buffer_size,
            'time_since_last_message': time_since_last,
            'has_pose_data': self.latest_pose is not None
        }
    
    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        logger.info("=== MQTT客户端统计 ===")
        logger.info(f"连接状态: {'已连接' if stats['is_connected'] else '未连接'}")
        logger.info(f"接收消息数: {stats['message_count']}")
        logger.info(f"缓冲区大小: {stats['buffer_size']}")
        logger.info(f"距上次消息: {stats['time_since_last_message']:.2f}秒")
        logger.info(f"有位姿数据: {'是' if stats['has_pose_data'] else '否'}")
