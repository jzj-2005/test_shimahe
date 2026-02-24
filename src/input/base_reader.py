"""
数据读取器基类
定义统一的数据读取接口
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple, Any
import numpy as np


class BaseReader(ABC):
    """数据读取器抽象基类"""
    
    def __init__(self):
        """初始化读取器"""
        self.is_opened = False
        self.frame_count = 0
        self.current_frame = 0
    
    @abstractmethod
    def open(self) -> bool:
        """
        打开数据源
        
        Returns:
            是否成功打开
        """
        pass
    
    @abstractmethod
    def read(self) -> Tuple[bool, Optional[np.ndarray], Optional[dict]]:
        """
        读取一帧数据
        
        Returns:
            (是否成功, 图像帧, 元数据)
        """
        pass
    
    @abstractmethod
    def close(self):
        """关闭数据源"""
        pass
    
    @abstractmethod
    def get_fps(self) -> float:
        """
        获取帧率
        
        Returns:
            帧率
        """
        pass
    
    @abstractmethod
    def get_frame_count(self) -> int:
        """
        获取总帧数
        
        Returns:
            总帧数
        """
        pass
    
    def __enter__(self):
        """支持with语句"""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持with语句"""
        self.close()
    
    def __iter__(self):
        """支持迭代"""
        return self
    
    def __next__(self) -> Tuple[np.ndarray, dict]:
        """
        迭代接口
        
        Returns:
            (图像帧, 元数据)
        """
        success, frame, metadata = self.read()
        if not success or frame is None:
            raise StopIteration
        return frame, metadata
