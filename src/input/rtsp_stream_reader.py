"""
RTSP视频流读取器
用于实时接收RTSP/RTMP视频流
"""

import cv2
import numpy as np
import time
import threading
from typing import Optional, Tuple
from collections import deque
from loguru import logger
from .base_reader import BaseReader


class RTSPStreamReader(BaseReader):
    """RTSP视频流读取器类"""
    
    def __init__(
        self,
        rtsp_url: str,
        buffer_size: int = 30,
        reconnect_interval: int = 5,
        max_reconnect_attempts: int = 0,
        transport_protocol: str = "tcp",
        connection_timeout: int = 10,
        read_timeout: int = 5
    ):
        """
        初始化RTSP流读取器
        
        Args:
            rtsp_url: RTSP流地址
            buffer_size: 帧缓冲区大小
            reconnect_interval: 断线重连间隔 (秒)
            max_reconnect_attempts: 最大重连次数 (0表示无限重连)
            transport_protocol: 传输协议 ("tcp" 或 "udp")
            connection_timeout: 连接超时 (秒)
            read_timeout: 读取超时 (秒)
        """
        super().__init__()
        self.rtsp_url = rtsp_url
        self.buffer_size = buffer_size
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.transport_protocol = transport_protocol
        self.connection_timeout = connection_timeout
        self.read_timeout = read_timeout
        
        self.cap = None
        self.fps = 0
        self.width = 0
        self.height = 0
        
        # 帧缓冲区
        self.frame_buffer = deque(maxlen=buffer_size)
        self.buffer_lock = threading.Lock()
        
        # 读取线程
        self.read_thread = None
        self.is_running = False
        self.reconnect_count = 0
        
        # 统计信息
        self.frame_received_count = 0
        self.last_receive_time = 0
    
    def open(self) -> bool:
        """
        打开RTSP流
        
        Returns:
            是否成功打开
        """
        return self._connect()
    
    def _connect(self) -> bool:
        """
        连接RTSP流
        
        Returns:
            是否成功连接
        """
        try:
            logger.info(f"正在连接RTSP流: {self.rtsp_url}")
            
            # 设置OpenCV的RTSP参数
            os_env = {}
            if self.transport_protocol.lower() == "tcp":
                os_env['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp'
            
            # 创建VideoCapture
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            
            # 设置超时
            self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, self.connection_timeout * 1000)
            self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, self.read_timeout * 1000)
            
            if not self.cap.isOpened():
                logger.error(f"无法打开RTSP流: {self.rtsp_url}")
                return False
            
            # 获取流属性
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # 如果FPS为0，设置默认值
            if self.fps == 0:
                self.fps = 30.0
            
            self.is_opened = True
            self.reconnect_count = 0
            
            logger.info(f"RTSP流已连接: 分辨率 {self.width}x{self.height}, 帧率 {self.fps:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"连接RTSP流时发生错误: {e}")
            return False
    
    def start(self):
        """启动后台读取线程"""
        if self.is_running:
            logger.warning("读取线程已在运行")
            return
        
        if not self.is_opened:
            if not self.open():
                logger.error("无法启动读取线程：流未打开")
                return
        
        self.is_running = True
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
        
        logger.info("RTSP流读取线程已启动")
    
    def _read_loop(self):
        """后台读取循环"""
        consecutive_failures = 0
        max_consecutive_failures = 10
        
        while self.is_running:
            try:
                if not self.is_opened or self.cap is None:
                    # 尝试重连
                    if self._should_reconnect():
                        logger.info(f"尝试重连... (第{self.reconnect_count + 1}次)")
                        if self._connect():
                            consecutive_failures = 0
                            continue
                        else:
                            self.reconnect_count += 1
                            time.sleep(self.reconnect_interval)
                            continue
                    else:
                        logger.error("达到最大重连次数，停止读取")
                        break
                
                # 读取帧
                ret, frame = self.cap.read()
                
                if ret and frame is not None:
                    timestamp = time.time() * 1000  # 毫秒
                    
                    # 添加到缓冲区
                    with self.buffer_lock:
                        self.frame_buffer.append((frame, timestamp))
                    
                    self.frame_received_count += 1
                    self.last_receive_time = time.time()
                    consecutive_failures = 0
                    
                else:
                    consecutive_failures += 1
                    logger.warning(f"读取帧失败 (连续失败{consecutive_failures}次)")
                    
                    if consecutive_failures >= max_consecutive_failures:
                        logger.error("连续读取失败次数过多，关闭连接")
                        self.is_opened = False
                        if self.cap:
                            self.cap.release()
                            self.cap = None
                    
                    time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"读取循环中发生错误: {e}")
                consecutive_failures += 1
                time.sleep(0.1)
        
        logger.info("RTSP流读取线程已停止")
    
    def _should_reconnect(self) -> bool:
        """
        判断是否应该尝试重连
        
        Returns:
            是否应该重连
        """
        if self.max_reconnect_attempts == 0:
            return True  # 无限重连
        
        return self.reconnect_count < self.max_reconnect_attempts
    
    def read(self) -> Tuple[bool, Optional[np.ndarray], Optional[dict]]:
        """
        从缓冲区读取一帧
        
        Returns:
            (是否成功, 图像帧, 元数据)
        """
        with self.buffer_lock:
            if len(self.frame_buffer) == 0:
                return False, None, None
            
            frame, timestamp = self.frame_buffer.popleft()
        
        metadata = {
            'timestamp': timestamp,
            'frame_number': self.frame_received_count,
            'width': self.width,
            'height': self.height,
            'fps': self.fps
        }
        
        return True, frame, metadata
    
    def get_frame(self) -> Optional[np.ndarray]:
        """
        快捷方法：获取最新的帧
        
        Returns:
            图像帧，如果没有则返回None
        """
        with self.buffer_lock:
            if len(self.frame_buffer) == 0:
                return None
            
            # 返回最新的帧
            frame, _ = self.frame_buffer[-1]
            return frame.copy()
    
    def get_buffer_size(self) -> int:
        """
        获取当前缓冲区大小
        
        Returns:
            缓冲区中的帧数
        """
        with self.buffer_lock:
            return len(self.frame_buffer)
    
    def clear_buffer(self):
        """清空帧缓冲区"""
        with self.buffer_lock:
            self.frame_buffer.clear()
        logger.info("帧缓冲区已清空")
    
    def stop(self):
        """停止读取线程"""
        self.is_running = False
        
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=5)
        
        logger.info("RTSP流读取已停止")
    
    def close(self):
        """关闭RTSP流"""
        self.stop()
        
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        self.is_opened = False
        logger.info("RTSP流已关闭")
    
    def get_fps(self) -> float:
        """获取流帧率"""
        return self.fps
    
    def get_frame_count(self) -> int:
        """获取已接收的帧总数"""
        return self.frame_received_count
    
    def get_stats(self) -> dict:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        time_since_last = time.time() - self.last_receive_time if self.last_receive_time > 0 else 0
        
        return {
            'total_frames': self.frame_received_count,
            'buffer_size': self.get_buffer_size(),
            'reconnect_count': self.reconnect_count,
            'is_connected': self.is_opened,
            'time_since_last_frame': time_since_last
        }
