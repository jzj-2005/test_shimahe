"""
本地视频文件读取器
用于读取MP4、MOV等格式的视频文件
"""

import cv2
import numpy as np
from typing import Optional, Tuple
from loguru import logger
from .base_reader import BaseReader


class VideoFileReader(BaseReader):
    """视频文件读取器类"""
    
    def __init__(
        self,
        video_path: str,
        frame_skip: int = 1,
        start_frame: int = 0,
        end_frame: int = 0
    ):
        """
        初始化视频文件读取器
        
        Args:
            video_path: 视频文件路径
            frame_skip: 跳帧间隔 (1表示读取每一帧)
            start_frame: 起始帧号
            end_frame: 结束帧号 (0表示读取到结束)
        """
        super().__init__()
        self.video_path = video_path
        self.frame_skip = frame_skip
        self.start_frame = start_frame
        self.end_frame = end_frame
        
        self.cap = None
        self.fps = 0
        self.width = 0
        self.height = 0
    
    def open(self) -> bool:
        """
        打开视频文件
        
        Returns:
            是否成功打开
        """
        try:
            self.cap = cv2.VideoCapture(self.video_path)
            
            if not self.cap.isOpened():
                logger.error(f"无法打开视频文件: {self.video_path}")
                return False
            
            # 获取视频属性
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # 设置起始帧
            if self.start_frame > 0:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)
                self.current_frame = self.start_frame
            
            # 设置结束帧
            if self.end_frame == 0 or self.end_frame > self.frame_count:
                self.end_frame = self.frame_count
            
            self.is_opened = True
            
            logger.info(f"视频文件已打开: {self.video_path}")
            logger.info(f"分辨率: {self.width}x{self.height}, 帧率: {self.fps:.2f}, 总帧数: {self.frame_count}")
            logger.info(f"处理范围: 第{self.start_frame}帧 到 第{self.end_frame}帧")
            
            return True
            
        except Exception as e:
            logger.error(f"打开视频文件时发生错误: {e}")
            return False
    
    def read(self) -> Tuple[bool, Optional[np.ndarray], Optional[dict]]:
        """
        读取一帧视频
        
        Returns:
            (是否成功, 图像帧, 元数据)
        """
        if not self.is_opened or self.cap is None:
            return False, None, None
        
        # 检查是否到达结束帧
        if self.current_frame >= self.end_frame:
            return False, None, None
        
        # 读取帧
        ret, frame = self.cap.read()
        
        if not ret or frame is None:
            logger.warning(f"无法读取第{self.current_frame}帧")
            return False, None, None
        
        # 计算时间戳 (毫秒)
        timestamp = (self.current_frame / self.fps) * 1000 if self.fps > 0 else 0
        
        # 构建元数据
        metadata = {
            'frame_number': self.current_frame,
            'timestamp': timestamp,
            'width': self.width,
            'height': self.height,
            'fps': self.fps
        }
        
        # 更新当前帧号
        self.current_frame += 1
        
        # 跳帧处理
        if self.frame_skip > 1:
            skip_count = self.frame_skip - 1
            for _ in range(skip_count):
                if self.current_frame < self.end_frame:
                    self.cap.read()
                    self.current_frame += 1
                else:
                    break
        
        return True, frame, metadata
    
    def close(self):
        """关闭视频文件"""
        if self.cap is not None:
            self.cap.release()
            self.is_opened = False
            logger.info(f"视频文件已关闭: {self.video_path}")
    
    def get_fps(self) -> float:
        """
        获取视频帧率
        
        Returns:
            帧率
        """
        return self.fps
    
    def get_frame_count(self) -> int:
        """
        获取视频总帧数
        
        Returns:
            总帧数
        """
        return self.frame_count
    
    def get_resolution(self) -> Tuple[int, int]:
        """
        获取视频分辨率
        
        Returns:
            (宽度, 高度)
        """
        return self.width, self.height
    
    def seek(self, frame_number: int) -> bool:
        """
        跳转到指定帧
        
        Args:
            frame_number: 目标帧号
            
        Returns:
            是否成功跳转
        """
        if not self.is_opened or self.cap is None:
            return False
        
        if frame_number < 0 or frame_number >= self.frame_count:
            logger.warning(f"帧号超出范围: {frame_number}")
            return False
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self.current_frame = frame_number
        
        return True
    
    def get_progress(self) -> float:
        """
        获取处理进度
        
        Returns:
            进度百分比 (0-100)
        """
        if self.end_frame <= self.start_frame:
            return 0.0
        
        total = self.end_frame - self.start_frame
        current = self.current_frame - self.start_frame
        
        return (current / total) * 100 if total > 0 else 0.0
