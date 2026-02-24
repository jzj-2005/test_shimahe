"""
图像保存模块
保存检测目标的截图
"""

import os
import cv2
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger


class ImageSaver:
    """图像保存器类"""
    
    def __init__(
        self,
        output_dir: str,
        save_format: str = "full",
        image_quality: int = 90
    ):
        """
        初始化图像保存器
        
        Args:
            output_dir: 图像输出目录
            save_format: 保存格式 ("crop"=裁剪目标区域, "full"=完整帧带标注)
            image_quality: 图像质量 (1-100)
        """
        self.output_dir = output_dir
        self.save_format = save_format
        self.image_quality = image_quality
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        self.save_count = 0
        
        logger.info(f"图像保存器初始化完成: {output_dir}")
    
    def save(
        self,
        image: np.ndarray,
        detection: Dict[str, Any],
        frame_number: int,
        detection_index: int = 0
    ) -> str:
        """
        保存检测目标图像
        
        Args:
            image: 原始图像
            detection: 检测结果字典
            frame_number: 帧号
            detection_index: 检测目标索引
            
        Returns:
            保存的图像路径
        """
        try:
            # 生成文件名
            class_name = detection.get('class_name', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            filename = f"frame_{frame_number:06d}_obj_{detection_index:03d}_{class_name}_{timestamp}.jpg"
            filepath = os.path.join(self.output_dir, filename)
            
            # 根据保存格式处理图像
            if self.save_format == "crop":
                save_image = self._crop_detection(image, detection)
            else:  # full
                save_image = self._draw_detection(image, detection)
            
            # 保存图像
            cv2.imwrite(filepath, save_image, [cv2.IMWRITE_JPEG_QUALITY, self.image_quality])
            
            self.save_count += 1
            logger.debug(f"图像已保存: {filename}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"保存图像失败: {e}")
            return ""
    
    def _crop_detection(self, image: np.ndarray, detection: Dict[str, Any]) -> np.ndarray:
        """
        裁剪检测目标区域
        
        Args:
            image: 原始图像
            detection: 检测结果
            
        Returns:
            裁剪后的图像
        """
        # 获取边界框
        corners = detection.get('corners', [])
        if len(corners) < 4:
            return image
        
        # 计算边界矩形
        xs = [c[0] for c in corners]
        ys = [c[1] for c in corners]
        
        x_min = max(0, int(min(xs)))
        y_min = max(0, int(min(ys)))
        x_max = min(image.shape[1], int(max(xs)))
        y_max = min(image.shape[0], int(max(ys)))
        
        # 裁剪
        cropped = image[y_min:y_max, x_min:x_max]
        
        return cropped
    
    def _draw_detection(self, image: np.ndarray, detection: Dict[str, Any]) -> np.ndarray:
        """
        在完整图像上绘制检测框
        
        Args:
            image: 原始图像
            detection: 检测结果
            
        Returns:
            绘制后的图像
        """
        img = image.copy()
        
        # 获取检测框
        corners = detection.get('corners', [])
        if len(corners) < 4:
            return img
        
        # 转换为整数坐标
        pts = np.array([[int(x), int(y)] for x, y in corners], dtype=np.int32)
        
        # 绘制矩形框
        cv2.polylines(img, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
        
        # 绘制标签
        class_name = detection.get('class_name', 'unknown')
        confidence = detection.get('confidence', 0)
        label = f"{class_name} {confidence:.2f}"
        
        # 计算标签位置
        x1, y1 = int(corners[0][0]), int(corners[0][1])
        
        # 绘制标签背景
        (text_width, text_height), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
        )
        cv2.rectangle(
            img,
            (x1, y1 - text_height - baseline - 5),
            (x1 + text_width, y1),
            (0, 255, 0),
            -1
        )
        
        # 绘制标签文本
        cv2.putText(
            img,
            label,
            (x1, y1 - baseline - 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )
        
        return img
    
    def save_batch(
        self,
        image: np.ndarray,
        detections: list,
        frame_number: int
    ) -> list:
        """
        批量保存检测目标
        
        Args:
            image: 原始图像
            detections: 检测结果列表
            frame_number: 帧号
            
        Returns:
            保存的图像路径列表
        """
        image_paths = []
        
        for i, detection in enumerate(detections):
            filepath = self.save(image, detection, frame_number, i)
            image_paths.append(filepath)
        
        return image_paths
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'output_dir': self.output_dir,
            'save_count': self.save_count,
            'save_format': self.save_format,
            'image_quality': self.image_quality
        }
    
    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        logger.info("=== 图像保存统计 ===")
        logger.info(f"输出目录: {stats['output_dir']}")
        logger.info(f"保存图像数: {stats['save_count']}")
        logger.info(f"保存格式: {stats['save_format']}")
