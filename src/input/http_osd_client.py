"""
HTTP OSD客户端
通过HTTP接口轮询获取无人机实时位姿数据（由开发部MQTT桥接服务提供）

接口: GET {base_url}{api_path}?devSn={dev_sn}
响应: { "code": 0, "msg": "", "data": { latitude, longitude, altitude, yaw, pitch, roll, ... } }
"""

import json
import time
import threading
from typing import Dict, Any, Optional, Callable
from collections import deque

import requests
from loguru import logger


class HttpOsdClient:
    """HTTP OSD数据客户端
    
    与DJIMQTTClient保持相同的外部接口，便于管道层统一调度。
    后台线程按可配置间隔轮询HTTP接口，解析响应并写入线程安全的位姿缓冲区。
    """

    def __init__(
        self,
        base_url: str,
        api_path: str = "/satxspace-airspace/ai/getDrone",
        dev_sn: str = "",
        poll_interval: float = 0.1,
        request_timeout: float = 2.0,
        max_retry: int = 3,
        pose_buffer_size: int = 100,
    ):
        """
        Args:
            base_url: 服务根地址，如 http://10.5.52.129:10006
            api_path: 接口路径
            dev_sn: 设备序列号
            poll_interval: 轮询间隔（秒），0.1 = 10Hz
            request_timeout: 单次请求超时（秒）
            max_retry: 连续失败达到此次数后标记为不可用
            pose_buffer_size: 位姿缓冲区容量
        """
        self.base_url = base_url.rstrip("/")
        self.api_path = api_path
        self.dev_sn = dev_sn
        self.poll_interval = poll_interval
        self.request_timeout = request_timeout
        self.max_retry = max_retry

        self.url = f"{self.base_url}{self.api_path}"

        # 位姿缓冲区
        self.pose_buffer: deque = deque(maxlen=pose_buffer_size)
        self.buffer_lock = threading.Lock()
        self.latest_pose: Optional[Dict[str, Any]] = None

        # 运行状态
        self.is_connected = False
        self._running = False
        self._poll_thread: Optional[threading.Thread] = None

        # 统计
        self.message_count = 0
        self.error_count = 0
        self.consecutive_errors = 0
        self.last_message_time: float = 0
        self.last_latency: float = 0

        # 复用TCP连接
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # 公共接口（与 DJIMQTTClient 对齐）
    # ------------------------------------------------------------------

    def connect(self, timeout: int = 10) -> bool:
        """验证接口可达并启动后台轮询线程"""
        logger.info(f"正在测试HTTP OSD接口: {self.url}?devSn={self.dev_sn}")

        try:
            resp = self._session.get(
                self.url,
                params={"devSn": self.dev_sn},
                timeout=min(timeout, self.request_timeout),
            )
            resp.raise_for_status()
            body = resp.json()

            if body.get("code") not in (0, 200):
                logger.error(f"HTTP OSD接口返回错误: code={body.get('code')}, msg={body.get('msg')}")
                return False

            data = body.get("data")
            if not data or not isinstance(data, dict):
                logger.error("HTTP OSD接口返回的data字段为空或格式异常")
                return False

            logger.info(f"HTTP OSD接口连接成功，收到 {len(data)} 个字段")
            self.is_connected = True

            # 解析首次数据
            self._parse_and_store(data, body)

            # 启动轮询线程
            self._running = True
            self._poll_thread = threading.Thread(
                target=self._poll_loop, daemon=True, name="http-osd-poll"
            )
            self._poll_thread.start()
            logger.info(f"HTTP OSD轮询线程已启动 (间隔 {self.poll_interval}s)")
            return True

        except requests.RequestException as e:
            logger.error(f"HTTP OSD接口连接失败: {e}")
            return False
        except Exception as e:
            logger.error(f"HTTP OSD初始化异常: {e}")
            return False

    def disconnect(self):
        """停止轮询线程并释放连接"""
        self._running = False
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=3)
        self._session.close()
        self.is_connected = False
        logger.info("HTTP OSD客户端已断开")

    def get_latest_pose(self) -> Optional[Dict[str, Any]]:
        """获取最新位姿数据（线程安全）"""
        with self.buffer_lock:
            return self.latest_pose.copy() if self.latest_pose else None

    def get_pose_buffer(self) -> list:
        """获取缓冲区副本"""
        with self.buffer_lock:
            return list(self.pose_buffer)

    def clear_buffer(self):
        """清空缓冲区"""
        with self.buffer_lock:
            self.pose_buffer.clear()
            self.latest_pose = None
        logger.info("HTTP OSD位姿缓冲区已清空")

    def get_stats(self) -> Dict[str, Any]:
        """获取运行统计（与DJIMQTTClient.get_stats格式一致）"""
        time_since_last = (
            time.time() - self.last_message_time if self.last_message_time > 0 else 0
        )
        with self.buffer_lock:
            buffer_size = len(self.pose_buffer)

        return {
            "is_connected": self.is_connected,
            "message_count": self.message_count,
            "buffer_size": buffer_size,
            "time_since_last_message": time_since_last,
            "has_pose_data": self.latest_pose is not None,
            "error_count": self.error_count,
            "consecutive_errors": self.consecutive_errors,
            "last_latency_ms": round(self.last_latency * 1000, 1),
        }

    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        logger.info("=== HTTP OSD客户端统计 ===")
        logger.info(f"连接状态: {'已连接' if stats['is_connected'] else '未连接'}")
        logger.info(f"成功接收: {stats['message_count']} 次")
        logger.info(f"累计错误: {stats['error_count']} 次 (连续 {stats['consecutive_errors']})")
        logger.info(f"缓冲区大小: {stats['buffer_size']}")
        logger.info(f"最近延迟: {stats['last_latency_ms']} ms")
        logger.info(f"距上次数据: {stats['time_since_last_message']:.2f}s")

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------

    def _poll_loop(self):
        """后台轮询主循环"""
        while self._running:
            t0 = time.time()
            try:
                resp = self._session.get(
                    self.url,
                    params={"devSn": self.dev_sn},
                    timeout=self.request_timeout,
                )
                resp.raise_for_status()
                body = resp.json()

                if body.get("code") not in (0, 200):
                    self._record_error(f"接口返回错误 code={body.get('code')}")
                    continue

                data = body.get("data")
                if not data or not isinstance(data, dict):
                    self._record_error("data字段为空")
                    continue

                self._parse_and_store(data, body)
                self.last_latency = time.time() - t0
                self.consecutive_errors = 0

            except requests.RequestException as e:
                self._record_error(str(e))
            except Exception as e:
                self._record_error(f"未知异常: {e}")
            finally:
                # 保持轮询节奏
                elapsed = time.time() - t0
                sleep_time = max(0, self.poll_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

    def _parse_and_store(self, data: Dict[str, Any], raw_response: Dict[str, Any]):
        """解析HTTP响应并存入缓冲区

        兼容 snake_case 和 camelCase 两种命名风格。
        输出的 pose 字典格式与 DJIMQTTClient 保持一致。
        """
        pose: Dict[str, Any] = {}

        # 时间戳：优先使用接口返回值
        pose["timestamp"] = raw_response.get("timestamp", time.time() * 1000)

        # ---------- 核心6字段（坐标转换必需）----------
        pose["latitude"] = _float(data, "latitude")
        pose["longitude"] = _float(data, "longitude")
        pose["altitude"] = _float(data, "altitude", fallback_keys=["altitude_above_sea_level"])
        pose["yaw"] = _float(data, "yaw", fallback_keys=["attitude_head"])
        pose["pitch"] = _float(data, "pitch", fallback_keys=["attitude_pitch"], default=-90)
        pose["roll"] = _float(data, "roll", fallback_keys=["attitude_roll"])

        # ---------- 扩展字段（保留供质量评估 / 下游使用）----------
        pose["gimbal_pitch"] = _float(data, "gimbal_pitch", camel="gimbalPitch")
        pose["gimbal_yaw"] = _float(data, "gimbal_yaw", camel="gimbalYaw")
        pose["gimbal_roll"] = _float(data, "gimbal_roll", camel="gimbalRoll")
        pose["satellite_count"] = _int(data, "satellite_count", camel="satelliteCount")
        pose["altitude_above_sea_level"] = _float(
            data, "altitude_above_sea_level", camel="altitudeAboveSeaLevel"
        )
        pose["relative_height"] = _float(data, "relative_height", camel="relativeHeight")
        pose["ground_speed"] = _float(data, "ground_speed", camel="groundSpeed")
        pose["velocity_z"] = _float(data, "velocity_z", camel="velocityZ")
        pose["battery_percent"] = _int(data, "battery_percent", camel="batteryPercent")

        # 标记数据来源
        pose["source"] = "http"

        # ---------- 数据校验 ----------
        if pose["latitude"] == 0 or pose["longitude"] == 0:
            logger.warning("HTTP OSD: GPS坐标为0，数据可能无效")
        if pose["altitude"] == 0:
            logger.warning("HTTP OSD: 高度为0，数据可能无效")

        # ---------- 写入缓冲区 ----------
        with self.buffer_lock:
            self.pose_buffer.append(pose)
            self.latest_pose = pose

        self.message_count += 1
        self.last_message_time = time.time()

        logger.debug(
            f"[HTTP OSD] GPS({pose['latitude']:.6f}, {pose['longitude']:.6f}), "
            f"高度{pose['altitude']:.1f}m, "
            f"姿态(yaw={pose['yaw']:.1f}°, pitch={pose['pitch']:.1f}°)"
        )

    def _record_error(self, msg: str):
        """记录错误并更新连续失败计数"""
        self.error_count += 1
        self.consecutive_errors += 1
        if self.consecutive_errors <= 3 or self.consecutive_errors % 10 == 0:
            logger.warning(f"HTTP OSD请求失败 (连续第{self.consecutive_errors}次): {msg}")
        if self.consecutive_errors >= self.max_retry:
            self.is_connected = False


# ======================================================================
# 辅助函数：安全地从字典中提取数值，兼容 snake_case / camelCase
# ======================================================================

def _float(
    data: Dict[str, Any],
    key: str,
    *,
    camel: str = "",
    fallback_keys: list = None,
    default: float = 0.0,
) -> float:
    """尝试多种键名取浮点值"""
    keys = [key]
    if camel:
        keys.append(camel)
    if fallback_keys:
        keys.extend(fallback_keys)
    for k in keys:
        val = data.get(k)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                pass
    return default


def _int(
    data: Dict[str, Any],
    key: str,
    *,
    camel: str = "",
    default: int = 0,
) -> int:
    """尝试多种键名取整型值"""
    for k in (key, camel) if camel else (key,):
        val = data.get(k)
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                pass
    return default
