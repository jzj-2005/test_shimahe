"""
OSD OCR识别器
使用PaddleOCR从视频帧的OSD区域提取飞行数据
"""

import re
import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from loguru import logger


class OSDOCRReader:
    """OSD OCR识别器类"""
    
    def __init__(
        self,
        roi_config: Optional[Dict[str, int]] = None,
        cache_enabled: bool = True,
        frame_interval: int = 5,
        use_gpu: bool = False,
        language: str = 'ch'
    ):
        """
        初始化OSD OCR识别器
        
        Args:
            roi_config: ROI区域配置 {'x': 0, 'y': 0, 'width': 600, 'height': 300}
            cache_enabled: 是否启用缓存
            frame_interval: OCR识别帧间隔（每N帧识别一次）
            use_gpu: 是否使用GPU加速
            language: OCR语言，'ch'(中文)或'en'(英文)
        """
        self.roi_config = roi_config or {'x': 0, 'y': 0, 'width': 600, 'height': 300}
        self.cache_enabled = cache_enabled
        self.frame_interval = frame_interval
        self.use_gpu = use_gpu
        self.language = language
        
        # 缓存相关
        self.last_pose = None
        self.last_ocr_frame = -999
        
        # 初始化PaddleOCR
        self._init_ocr()
        
        logger.info(f"OSD OCR识别器初始化完成")
        logger.info(f"ROI区域: {self.roi_config}")
        logger.info(f"帧间隔: {self.frame_interval}, GPU: {self.use_gpu}")
    
    def _init_ocr(self):
        """初始化PaddleOCR引擎"""
        try:
            from paddleocr import PaddleOCR
            
            # PaddleOCR 3.x+ 使用device参数代替use_gpu
            device = 'gpu' if self.use_gpu else 'cpu'
            
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang=self.language,
                device=device
            )
            
            logger.info("PaddleOCR引擎初始化成功")
            
        except ImportError:
            logger.error("PaddleOCR未安装，请运行: pip install paddleocr paddlepaddle")
            raise
        except Exception as e:
            logger.error(f"PaddleOCR初始化失败: {e}")
            raise
    
    def extract_pose_from_frame(
        self,
        frame: np.ndarray,
        frame_number: int,
        timestamp: float
    ) -> Optional[Dict[str, Any]]:
        """
        从视频帧中提取位姿数据
        
        Args:
            frame: 视频帧图像
            frame_number: 帧号
            timestamp: 时间戳（毫秒）
            
        Returns:
            位姿数据字典，格式与SRT解析器保持一致
        """
        # 检查是否需要OCR（基于帧间隔）
        if frame_number - self.last_ocr_frame < self.frame_interval:
            # 使用缓存的位姿数据
            if self.cache_enabled and self.last_pose:
                # 更新时间戳和帧号
                cached_pose = self.last_pose.copy()
                cached_pose['frame_number'] = frame_number
                cached_pose['timestamp'] = timestamp
                return cached_pose
            return None
        
        # 更新OCR帧号
        self.last_ocr_frame = frame_number
        
        try:
            # 1. 提取ROI区域
            roi = self._extract_roi(frame)
            
            # 2. OCR识别
            text_lines = self._ocr_region(roi)
            
            if not text_lines:
                logger.warning(f"帧 {frame_number}: OCR未识别到任何文字")
                return None
            
            # 3. 解析OSD文本
            pose = self._parse_osd_text(text_lines)
            
            if not pose:
                logger.warning(f"帧 {frame_number}: 解析OSD失败")
                return None
            
            # 4. 添加帧号和时间戳
            pose['frame_number'] = frame_number
            pose['timestamp'] = timestamp
            pose['block_number'] = frame_number  # 兼容SRT格式
            
            # 5. 缓存结果
            if self.cache_enabled:
                self.last_pose = pose
            
            logger.debug(f"帧 {frame_number}: OCR提取成功 - "
                        f"GPS: ({pose.get('latitude', 0):.6f}, {pose.get('longitude', 0):.6f}), "
                        f"高度: {pose.get('altitude', 0):.1f}m")
            
            return pose
            
        except Exception as e:
            logger.error(f"帧 {frame_number} OCR提取失败: {e}")
            return None
    
    def _extract_roi(self, frame: np.ndarray) -> np.ndarray:
        """
        提取ROI区域
        
        Args:
            frame: 完整视频帧
            
        Returns:
            ROI区域图像
        """
        x = self.roi_config['x']
        y = self.roi_config['y']
        w = self.roi_config['width']
        h = self.roi_config['height']
        
        # 确保ROI在图像范围内
        height, width = frame.shape[:2]
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))
        w = min(w, width - x)
        h = min(h, height - y)
        
        roi = frame[y:y+h, x:x+w]
        return roi
    
    def _ocr_region(self, image_roi: np.ndarray) -> List[str]:
        """
        对ROI区域进行OCR识别
        
        Args:
            image_roi: ROI区域图像
            
        Returns:
            识别到的文本行列表
        """
        try:
            # PaddleOCR识别 - 新版API
            result = self.ocr.ocr(image_roi)
            
            if not result or not result[0]:
                return []
            
            # 提取文本
            text_lines = []
            for line in result[0]:
                if line and len(line) >= 2:
                    text = line[1][0]  # 文本内容
                    confidence = line[1][1]  # 置信度
                    
                    # 过滤低置信度结果
                    if confidence > 0.5:
                        text_lines.append(text)
            
            return text_lines
            
        except Exception as e:
            logger.error(f"OCR识别失败: {e}")
            return []
    
    def _parse_osd_text(self, text_lines: List[str]) -> Optional[Dict[str, Any]]:
        """
        解析OSD文本，提取飞行数据
        
        Args:
            text_lines: OCR识别的文本行列表
            
        Returns:
            位姿数据字典
        """
        # 合并所有文本行
        full_text = ' '.join(text_lines)
        
        pose = {}
        
        # 解析GPS坐标
        # 格式示例1: latitude: 31.123456 或 longitude: 120.123456
        # 格式示例2: 22.784800°N 114.105067°E (实际OSD格式)
        lat_patterns = [
            r'latitude[:\s]*([+-]?\d+\.\d+)',
            r'([+-]?\d+\.\d+)[°\s]*[Nn]',  # 新增：匹配 "22.784800°N" 格式
            r'[Nn][:\s]*([+-]?\d+\.\d+)',
            r'纬度[:\s]*([+-]?\d+\.\d+)'
        ]
        
        lon_patterns = [
            r'longitude[:\s]*([+-]?\d+\.\d+)',
            r'([+-]?\d+\.\d+)[°\s]*[Ee]',  # 新增：匹配 "114.105067°E" 格式
            r'[Ee][:\s]*([+-]?\d+\.\d+)',
            r'经度[:\s]*([+-]?\d+\.\d+)'
        ]
        
        for pattern in lat_patterns:
            lat_match = re.search(pattern, full_text, re.IGNORECASE)
            if lat_match:
                try:
                    pose['latitude'] = float(lat_match.group(1))
                    break
                except ValueError:
                    continue
        
        for pattern in lon_patterns:
            lon_match = re.search(pattern, full_text, re.IGNORECASE)
            if lon_match:
                try:
                    pose['longitude'] = float(lon_match.group(1))
                    break
                except ValueError:
                    continue
        
        # 解析高度
        # 格式示例: 
        # - altitude: 100.5m
        # - H100.5
        # - "114.105067°E 139" (E后面的数字)
        # - "139.369m" (数字+m)
        alt_patterns = [
            r'altitude[:\s]*([+-]?\d+\.?\d*)',  # altitude: 100.5
            r'[Hh][:\s]*([+-]?\d+\.?\d*)',      # H100.5
            r'高度[:\s]*([+-]?\d+\.?\d*)',        # 高度: 100.5
            r'[Ee]\s+([+-]?\d+\.?\d*)[mM]?',    # E后面跟空格和数字 (最常见的OSD格式)
            r'([+-]?\d+\.?\d*)[mM]\s*$'         # 行尾的数字+m
        ]
        
        for pattern in alt_patterns:
            alt_match = re.search(pattern, full_text, re.IGNORECASE)
            if alt_match:
                try:
                    pose['altitude'] = float(alt_match.group(1))
                    break
                except ValueError:
                    continue
        
        # 解析姿态角（可选）
        # 格式示例: yaw: 90.5, pitch: -10.2, roll: 5.3
        yaw_match = re.search(r'yaw[:\s]*([+-]?\d+\.?\d*)', full_text, re.IGNORECASE)
        if yaw_match:
            try:
                pose['yaw'] = float(yaw_match.group(1))
            except ValueError:
                pass
        
        pitch_match = re.search(r'pitch[:\s]*([+-]?\d+\.?\d*)', full_text, re.IGNORECASE)
        if pitch_match:
            try:
                pose['pitch'] = float(pitch_match.group(1))
            except ValueError:
                pass
        
        roll_match = re.search(r'roll[:\s]*([+-]?\d+\.?\d*)', full_text, re.IGNORECASE)
        if roll_match:
            try:
                pose['roll'] = float(roll_match.group(1))
            except ValueError:
                pass
        
        # 解析日期时间（可选）
        # 格式示例: 2024-02-12 10:30:45.123
        datetime_match = re.search(
            r'(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}:\d{2}\.?\d*)',
            full_text
        )
        if datetime_match:
            pose['datetime'] = datetime_match.group(1)
        
        # 检查是否至少有GPS坐标
        if 'latitude' not in pose or 'longitude' not in pose:
            logger.debug(f"未能提取GPS坐标，识别文本: {full_text[:100]}...")
            return None
        
        return pose
    
    def reset_cache(self):
        """重置缓存"""
        self.last_pose = None
        self.last_ocr_frame = -999
        logger.debug("OCR缓存已重置")
    
    def get_last_pose(self) -> Optional[Dict[str, Any]]:
        """
        获取最后一次识别的位姿数据
        
        Returns:
            位姿数据字典
        """
        return self.last_pose
