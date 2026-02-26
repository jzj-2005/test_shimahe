"""
检测模块
包括YOLO检测引擎和目标跟踪管理器
"""

from .yolo_detector import YOLODetector
from .track_manager import TrackManager

__all__ = ['YOLODetector', 'TrackManager']
