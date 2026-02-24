"""
图片序列读取器
用于读取正射图片序列（如DJI无人机拍摄的JPEG图片）
"""

import os
import re
import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime, timedelta, timezone
from pathlib import Path
from loguru import logger
from .base_reader import BaseReader


class ImageSequenceReader(BaseReader):
    """图片序列读取器类"""
    
    def __init__(
        self,
        image_dir: str,
        image_pattern: str = "*.jpeg",
        start_index: int = 0,
        end_index: int = 0,
        skip: int = 1
    ):
        """
        初始化图片序列读取器
        
        Args:
            image_dir: 图片目录路径
            image_pattern: 图片文件匹配模式（如 "*.jpeg", "*.jpg", "DJI_*.jpeg"）
            start_index: 起始索引
            end_index: 结束索引 (0表示读取到最后)
            skip: 跳帧间隔 (1表示读取每一张)
        """
        super().__init__()
        self.image_dir = image_dir
        self.image_pattern = image_pattern
        self.start_index = start_index
        self.end_index = end_index
        self.skip = skip
        
        self.image_files = []
        self.current_index = 0
    
    def open(self) -> bool:
        """
        打开图片序列（扫描目录，收集图片文件）
        
        Returns:
            是否成功打开
        """
        try:
            image_dir_path = Path(self.image_dir)
            
            if not image_dir_path.exists():
                logger.error(f"图片目录不存在: {self.image_dir}")
                return False
            
            # 收集所有匹配的图片文件
            if self.image_pattern.startswith("*."):
                # 简单扩展名匹配
                extension = self.image_pattern[1:]  # 去掉 "*"
                all_files = [f for f in image_dir_path.glob(f"*{extension}")]
            else:
                # 使用glob模式匹配
                all_files = list(image_dir_path.glob(self.image_pattern))
            
            # 按文件名排序
            all_files.sort()
            
            # 转换为字符串路径
            self.image_files = [str(f) for f in all_files]
            
            if not self.image_files:
                logger.error(f"未找到匹配的图片文件: {self.image_dir}/{self.image_pattern}")
                return False
            
            # 设置索引范围
            self.frame_count = len(self.image_files)
            
            if self.end_index == 0 or self.end_index > self.frame_count:
                self.end_index = self.frame_count
            
            self.current_index = self.start_index
            self.current_frame = self.start_index
            
            self.is_opened = True
            
            logger.info(f"图片序列已打开: {self.image_dir}")
            logger.info(f"总图片数: {self.frame_count}, 处理范围: {self.start_index} - {self.end_index}")
            
            return True
            
        except Exception as e:
            logger.error(f"打开图片序列时发生错误: {e}")
            return False
    
    def read(self) -> Tuple[bool, Optional[np.ndarray], Optional[dict]]:
        """
        读取下一张图片
        
        Returns:
            (是否成功, 图像, 元数据)
        """
        if not self.is_opened:
            return False, None, None
        
        # 检查是否到达结束索引
        if self.current_index >= self.end_index:
            return False, None, None
        
        try:
            # 读取当前图片
            image_path = self.image_files[self.current_index]
            image = cv2.imread(image_path)
            
            if image is None:
                logger.warning(f"无法读取图片: {image_path}")
                self.current_index += self.skip
                self.current_frame += self.skip
                return False, None, None
            
            # 提取元数据
            filename = os.path.basename(image_path)
            timestamp = self._extract_timestamp_from_filename(filename)
            
            metadata = {
                'frame_number': self.current_index,
                'filename': filename,
                'filepath': image_path,
                'timestamp': timestamp,
                'width': image.shape[1],
                'height': image.shape[0]
            }
            
            # 更新索引
            self.current_index += self.skip
            self.current_frame += self.skip
            
            return True, image, metadata
            
        except Exception as e:
            logger.error(f"读取图片时发生错误: {e}")
            return False, None, None
    
    def _extract_timestamp_from_filename(self, filename: str) -> float:
        """
        从文件名提取时间戳
        
        支持的格式：
        - DJI_YYYYMMDDHHMMSS_序号_V.jpeg
        - IMG_YYYYMMDD_HHMMSS.jpeg
        
        注意：DJI文件名时间为北京时间（UTC+8），需要转换为UTC以匹配GPS时间
        
        Args:
            filename: 文件名
            
        Returns:
            时间戳（毫秒），如果无法提取则返回0
        """
        try:
            # DJI格式: DJI_20260204142622_0001_V.jpeg
            match = re.search(r'DJI_(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})', filename)
            if match:
                year, month, day, hour, minute, second = map(int, match.groups())
                # DJI文件名是北京时间（UTC+8），需要转换为UTC时间
                dt_beijing = datetime(year, month, day, hour, minute, second)
                # 减去8小时得到UTC时间，并明确指定UTC时区
                dt_utc = (dt_beijing - timedelta(hours=8)).replace(tzinfo=timezone.utc)
                # 转换为毫秒时间戳
                timestamp = dt_utc.timestamp() * 1000
                return timestamp
            
            # IMG格式: IMG_20260204_142622.jpeg
            match = re.search(r'IMG_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', filename)
            if match:
                year, month, day, hour, minute, second = map(int, match.groups())
                dt = datetime(year, month, day, hour, minute, second)
                timestamp = dt.timestamp() * 1000
                return timestamp
            
            # 如果无法提取，使用序号作为相对时间
            seq_match = re.search(r'_(\d{4,})_', filename)
            if seq_match:
                sequence = int(seq_match.group(1))
                return float(sequence) * 1000  # 序号 * 1000作为伪时间戳
            
            logger.debug(f"无法从文件名提取时间戳: {filename}")
            return 0.0
            
        except Exception as e:
            logger.debug(f"时间戳提取失败: {e}")
            return 0.0
    
    def close(self):
        """关闭图片序列"""
        self.is_opened = False
        self.image_files = []
        logger.info("图片序列已关闭")
    
    def get_fps(self) -> float:
        """
        获取"帧率"（图片序列返回0，表示静态序列）
        
        Returns:
            0.0
        """
        return 0.0
    
    def get_frame_count(self) -> int:
        """
        获取总图片数
        
        Returns:
            总图片数
        """
        return self.frame_count
    
    def get_image_list(self) -> List[str]:
        """
        获取所有图片文件路径列表
        
        Returns:
            图片路径列表
        """
        return self.image_files.copy()
    
    def get_progress(self) -> float:
        """
        获取处理进度
        
        Returns:
            进度百分比 (0-100)
        """
        if self.end_index <= self.start_index:
            return 0.0
        
        total = self.end_index - self.start_index
        current = self.current_index - self.start_index
        
        return (current / total) * 100 if total > 0 else 0.0
    
    def seek(self, index: int) -> bool:
        """
        跳转到指定索引
        
        Args:
            index: 目标索引
            
        Returns:
            是否成功跳转
        """
        if not self.is_opened:
            return False
        
        if index < 0 or index >= self.frame_count:
            logger.warning(f"索引超出范围: {index}")
            return False
        
        self.current_index = index
        self.current_frame = index
        
        return True
    
    def print_info(self):
        """打印图片序列信息"""
        logger.info("=== 图片序列信息 ===")
        logger.info(f"目录: {self.image_dir}")
        logger.info(f"匹配模式: {self.image_pattern}")
        logger.info(f"总图片数: {self.frame_count}")
        logger.info(f"处理范围: {self.start_index} - {self.end_index}")
        logger.info(f"跳帧间隔: {self.skip}")
        
        if self.image_files:
            logger.info(f"第一张: {os.path.basename(self.image_files[0])}")
            logger.info(f"最后一张: {os.path.basename(self.image_files[-1])}")
