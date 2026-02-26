"""
报告生成器
统一管理检测结果的输出
"""

import os
from typing import List, Dict, Any
import numpy as np
from loguru import logger
from .csv_writer import CSVWriter
from .image_saver import ImageSaver


class ReportGenerator:
    """报告生成器类"""
    
    def __init__(
        self,
        csv_path: str,
        image_dir: str,
        save_images: bool = True,
        image_format: str = "full",
        image_quality: int = 90,
        csv_write_mode: str = "overwrite",
        post_process_config: dict = None
    ):
        """
        初始化报告生成器
        
        Args:
            csv_path: CSV文件路径
            image_dir: 图像保存目录
            save_images: 是否保存图像
            image_format: 图像保存格式
            image_quality: 图像质量
            csv_write_mode: CSV写入模式
            post_process_config: 后处理配置（可选）
        """
        self.csv_path = csv_path
        self.image_dir = image_dir
        self.save_images = save_images
        
        # 初始化CSV写入器
        self.csv_writer = CSVWriter(csv_path, csv_write_mode)
        
        # 初始化图像保存器
        self.image_saver = None
        if save_images:
            self.image_saver = ImageSaver(image_dir, image_format, image_quality)
        
        # 初始化后处理器（v2.1新增）
        self.post_processor = None
        if post_process_config:
            try:
                from .post_processor import PostProcessor
                self.post_processor = PostProcessor(post_process_config)
                if self.post_processor.is_enabled():
                    logger.info("✓ 后处理器已启用（将在检测完成后自动执行）")
            except Exception as e:
                logger.warning(f"后处理器初始化失败: {e}，将跳过后处理")
                self.post_processor = None
        
        logger.info("报告生成器初始化完成")
    
    def save(
        self,
        detections: List[Dict[str, Any]],
        image: np.ndarray,
        pose: Dict[str, Any],
        frame_number: int
    ):
        """
        保存检测结果
        
        Args:
            detections: 检测结果列表
            image: 图像帧
            pose: 位姿数据
            frame_number: 帧号
        """
        if not detections:
            return
        
        try:
            # 保存图像（如果启用）
            image_paths = []
            if self.save_images and self.image_saver:
                image_paths = self.image_saver.save_batch(image, detections, frame_number)
            
            # 写入CSV
            for i, detection in enumerate(detections):
                image_path = image_paths[i] if i < len(image_paths) else ""
                self.csv_writer.write(detection, pose, frame_number, image_path)
            
            logger.debug(f"帧 {frame_number} 的 {len(detections)} 个检测结果已保存")
            
        except Exception as e:
            logger.error(f"保存检测结果时发生错误: {e}")
    
    def save_realtime(
        self,
        detections: List[Dict[str, Any]],
        image: np.ndarray,
        pose: Dict[str, Any],
        frame_number: int
    ):
        """
        实时模式下保存检测结果 (与save相同，保留用于未来扩展)
        
        Args:
            detections: 检测结果列表
            image: 图像帧
            pose: 位姿数据
            frame_number: 帧号
        """
        self.save(detections, image, pose, frame_number)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        csv_stats = self.csv_writer.get_stats()
        
        stats = {
            'csv_path': self.csv_path,
            'csv_write_count': csv_stats['write_count'],
            'save_images': self.save_images
        }
        
        if self.save_images and self.image_saver:
            image_stats = self.image_saver.get_stats()
            stats['image_dir'] = self.image_dir
            stats['image_save_count'] = image_stats['save_count']
        
        return stats
    
    def close(self):
        """关闭报告生成器，释放资源，并执行后处理"""
        # 1. 关闭CSV写入器
        if hasattr(self, 'csv_writer') and self.csv_writer is not None:
            self.csv_writer.close()
        
        # 2. 执行后处理（v2.1新增）
        if hasattr(self, 'post_processor') and self.post_processor is not None:
            if self.post_processor.is_enabled():
                try:
                    # 确定输出基础目录
                    output_base_dir = os.path.dirname(os.path.dirname(self.csv_path))
                    
                    # 执行后处理
                    results = self.post_processor.process(
                        csv_path=self.csv_path,
                        output_base_dir=output_base_dir
                    )
                    
                    if results.get('success'):
                        logger.info("✓ 后处理任务全部完成")
                    else:
                        logger.warning("后处理未完全成功，请检查日志")
                        
                except Exception as e:
                    logger.error(f"后处理执行失败: {e}", exc_info=True)
        
        logger.info("报告生成器已关闭")
    
    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        logger.info("=== 报告生成统计 ===")
        logger.info(f"CSV文件: {stats['csv_path']}")
        logger.info(f"CSV记录数: {stats['csv_write_count']}")
        
        if stats.get('save_images'):
            logger.info(f"图像目录: {stats.get('image_dir', 'N/A')}")
            logger.info(f"保存图像数: {stats.get('image_save_count', 0)}")
