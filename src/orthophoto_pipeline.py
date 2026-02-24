"""
正射图片处理流程
处理正射图片序列 + RTK位姿数据
"""

import time
import os
from pathlib import Path
from typing import Optional
from tqdm import tqdm
from loguru import logger

from .utils.config_loader import ConfigLoader
from .utils.logger import setup_logger
from .utils.data_sync import DataSynchronizer
from .utils.visualizer import Visualizer

from .input.image_sequence_reader import ImageSequenceReader
from .input.mrk_parser import MRKParser

from .detection.yolo_detector import YOLODetector
from .transform.camera_model import CameraModel
from .transform.coord_transform import CoordinateTransformer
from .output.report_generator import ReportGenerator


class OrthophotoPipeline:
    """正射图片处理流程类"""
    
    def __init__(self, config_dir: str = "./config"):
        """
        初始化正射图片处理流程
        
        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = config_dir
        self.config_loader = ConfigLoader(config_dir)
        
        # 加载配置
        self.orthophoto_config = self.config_loader.load('orthophoto_config')
        self.yolo_config = self.config_loader.load('yolo_config')
        self.camera_config = self.config_loader.load('camera_params')
        
        # 初始化日志
        log_config = self.orthophoto_config.get('logging', {})
        setup_logger(
            log_level=log_config.get('level', 'INFO'),
            log_file=log_config.get('log_file') if log_config.get('save_to_file') else None
        )
        
        # 初始化组件
        self._init_components()
        
        logger.info("正射图片处理流程初始化完成")
    
    def _init_components(self):
        """初始化各个组件"""
        # MRK解析器
        self.mrk_parser = MRKParser()
        
        # 数据同步器
        sync_config = self.orthophoto_config.get('data_sync', {})
        self.synchronizer = DataSynchronizer(
            sync_method='timestamp',
            timestamp_tolerance=sync_config.get('time_tolerance', 5000.0),
            max_time_diff=sync_config.get('time_tolerance', 5000.0)
        )
        
        # YOLO检测器
        model_config = self.yolo_config.get('model', {})
        detection_config = self.yolo_config.get('detection', {})
        classes_config = self.yolo_config.get('classes', {})
        
        self.detector = YOLODetector(
            model_path=model_config.get('path', './models/yolo11x.pt'),
            confidence_threshold=detection_config.get('confidence_threshold', 0.5),
            iou_threshold=detection_config.get('iou_threshold', 0.45),
            device=model_config.get('device', 'cuda'),
            half_precision=model_config.get('half_precision', False),
            imgsz=detection_config.get('imgsz', 640),
            class_names=classes_config.get('names', {}),
            target_classes=classes_config.get('target_classes')
        )
        
        # 坐标转换器
        self.camera_model = CameraModel(self.camera_config)
        self.transformer = CoordinateTransformer(self.camera_model)
        
        # 报告生成器
        output_config = self.orthophoto_config.get('output', {})
        self.report_gen = ReportGenerator(
            csv_path=output_config.get('csv_path', './data/output/csv/detections_orthophoto.csv'),
            image_dir=output_config.get('image_dir', './data/output/images/orthophoto/'),
            save_images=output_config.get('save_images', True),
            image_format=output_config.get('image_format', 'full'),
            image_quality=output_config.get('image_quality', 85),
            csv_write_mode=output_config.get('csv_write_mode', 'overwrite')
        )
        
        # 可视化器
        viz_config = self.orthophoto_config.get('visualization', {})
        self.visualizer = None
        if viz_config.get('realtime_display', False):
            self.visualizer = Visualizer(
                display_width=viz_config.get('display_width', 1280),
                display_height=viz_config.get('display_height', 720),
                box_color=tuple(viz_config.get('box_color', [0, 255, 0])),
                box_thickness=viz_config.get('box_thickness', 2)
            )
    
    def run(self, image_dir: Optional[str] = None, mrk_file: Optional[str] = None):
        """
        运行正射图片处理流程
        
        Args:
            image_dir: 图片目录路径 (如果为None，从配置中读取)
            mrk_file: MRK文件路径 (如果为None，从配置或自动查找)
        """
        # 获取图片目录
        input_config = self.orthophoto_config.get('input', {})
        if image_dir is None:
            image_dir = input_config.get('image_dir')
        
        if not image_dir:
            logger.error("未指定图片目录路径")
            return
        
        logger.info(f"开始处理正射图片: {image_dir}")
        
        try:
            # 1. 查找或指定MRK文件
            logger.info("步骤1: 查找MRK文件")
            if mrk_file is None:
                mrk_file = self._find_mrk_file(image_dir, input_config)
            
            if not mrk_file:
                logger.error("无法找到MRK文件，处理终止")
                return
            
            # 2. 解析MRK文件
            logger.info("步骤2: 解析MRK位姿数据")
            pose_data = self.mrk_parser.parse(mrk_file)
            
            if not pose_data:
                logger.error("MRK解析失败，处理终止")
                return
            
            # 打印示例位姿数据
            self.mrk_parser.print_sample(3)
            
            # 将位姿数据添加到同步器
            for pose in pose_data:
                self.synchronizer.add_pose(pose)
            
            # 3. 打开图片序列
            logger.info("步骤3: 打开图片序列")
            image_pattern = input_config.get('image_pattern', '*.jpeg')
            start_index = input_config.get('start_index', 0)
            end_index = input_config.get('end_index', 0)
            skip = input_config.get('skip', 1)
            
            image_reader = ImageSequenceReader(
                image_dir=image_dir,
                image_pattern=image_pattern,
                start_index=start_index,
                end_index=end_index,
                skip=skip
            )
            
            if not image_reader.open():
                logger.error("无法打开图片序列")
                return
            
            image_reader.print_info()
            
            # 4. 逐图片处理
            logger.info("步骤4: 开始逐图片处理")
            self._process_images(image_reader)
            
            # 5. 关闭资源
            image_reader.close()
            if self.visualizer:
                self.visualizer.close()
            
            # 6. 打印统计信息
            self._print_stats()
            
            logger.info("正射图片处理完成")
            
        except KeyboardInterrupt:
            logger.warning("处理被用户中断")
        except Exception as e:
            logger.error(f"处理过程中发生错误: {e}", exc_info=True)
        finally:
            # 关闭报告生成器（释放CSV文件句柄）
            if self.report_generator:
                try:
                    self.report_generator.close()
                except Exception as e:
                    logger.warning(f"关闭报告生成器时出错: {e}")
            
            # 关闭可视化
            if self.visualizer:
                try:
                    self.visualizer.close()
                except Exception as e:
                    logger.warning(f"关闭可视化窗口时出错: {e}")
    
    def _find_mrk_file(self, image_dir: str, input_config: dict) -> Optional[str]:
        """
        查找MRK文件
        
        Args:
            image_dir: 图片目录
            input_config: 输入配置
            
        Returns:
            MRK文件路径，如果未找到则返回None
        """
        # 如果配置中指定了MRK文件且存在，直接使用
        mrk_file = input_config.get('mrk_file', '')
        if mrk_file and os.path.exists(mrk_file):
            logger.info(f"使用指定的MRK文件: {mrk_file}")
            return mrk_file
        
        # 如果启用了自动查找
        if input_config.get('auto_find_mrk', True):
            # 在图片目录中查找.MRK文件
            image_dir_path = Path(image_dir)
            mrk_files = list(image_dir_path.glob('*.MRK'))
            
            if mrk_files:
                # 使用第一个找到的MRK文件
                mrk_file = str(mrk_files[0])
                logger.info(f"自动找到MRK文件: {mrk_file}")
                if len(mrk_files) > 1:
                    logger.warning(f"找到多个MRK文件 ({len(mrk_files)}个)，使用第一个")
                return mrk_file
        
        return None
    
    def _process_images(self, image_reader: ImageSequenceReader):
        """
        逐图片处理
        
        Args:
            image_reader: 图片序列读取器
        """
        edge_config = self.orthophoto_config.get('edge_detection', {})
        check_edge = edge_config.get('enabled', True)
        edge_threshold = edge_config.get('edge_threshold', 50)
        
        stats_config = self.orthophoto_config.get('statistics', {})
        stats_enabled = stats_config.get('enabled', True)
        stats_interval = stats_config.get('output_interval', 50)
        
        total_images = image_reader.get_frame_count()
        
        # 创建进度条
        pbar = tqdm(total=total_images, desc="处理进度")
        
        image_count = 0
        detection_count = 0
        edge_detection_count = 0
        fps_start_time = time.time()
        fps_image_count = 0
        current_fps = 0
        
        while True:
            # 读取图片
            success, image, metadata = image_reader.read()
            
            if not success or image is None:
                break
            
            frame_number = metadata['frame_number']
            image_timestamp = metadata['timestamp']
            filename = metadata['filename']
            
            # 调试：打印第一张图片的时间戳
            if frame_number == 0:
                from datetime import datetime, timezone
                logger.info(f"【调试】第一张图片: {filename}")
                logger.info(f"【调试】图片时间戳: {image_timestamp}ms = {datetime.fromtimestamp(image_timestamp/1000, tz=timezone.utc)}")
                if self.mrk_parser and self.mrk_parser.pose_data:
                    first_pose = self.mrk_parser.pose_data[0]
                    logger.info(f"【调试】第一个GPS时间戳: {first_pose['timestamp']}ms = {datetime.fromtimestamp(first_pose['timestamp']/1000, tz=timezone.utc)}")
                    logger.info(f"【调试】时间差: {abs(image_timestamp - first_pose['timestamp'])/1000}秒")
            
            # 同步位姿数据
            pose = self.synchronizer.sync_frame_with_pose(image_timestamp, frame_number)
            
            if pose is None:
                logger.warning(f"图片 {filename} (索引{frame_number}) 未找到匹配的位姿数据，跳过")
                pbar.update(1)
                continue
            
            # YOLO检测（带边缘检测）
            detections = self.detector.detect(
                image,
                return_type='corners',
                check_edge=check_edge,
                edge_threshold=edge_threshold
            )
            
            # 统计边缘检测数量
            for det in detections:
                if det.get('is_on_edge', False):
                    edge_detection_count += 1
            
            # 坐标转换
            if detections:
                detections = self.transformer.transform_detections(detections, pose)
                detection_count += len(detections)
            
            # 保存结果
            if detections:
                self.report_gen.save(detections, image, pose, frame_number)
            
            # 可视化
            if self.visualizer:
                # 计算FPS
                fps_image_count += 1
                if fps_image_count % 10 == 0:
                    elapsed = time.time() - fps_start_time
                    current_fps = fps_image_count / elapsed if elapsed > 0 else 0
                
                key = self.visualizer.show(image, detections, pose, frame_number, current_fps)
                
                # 按ESC退出
                if key == 27:
                    logger.info("用户按下ESC键，退出处理")
                    break
            
            image_count += 1
            pbar.update(1)
            
            # 定期输出统计
            if stats_enabled and image_count % stats_interval == 0:
                self._print_interim_stats(image_count, detection_count, edge_detection_count, current_fps)
        
        pbar.close()
        
        logger.info(f"共处理 {image_count} 张图片，检测到 {detection_count} 个目标，其中 {edge_detection_count} 个在边缘")
    
    def _print_interim_stats(self, image_count: int, detection_count: int, edge_detection_count: int, fps: float):
        """打印中间统计信息"""
        avg_detections = detection_count / image_count if image_count > 0 else 0
        edge_ratio = (edge_detection_count / detection_count * 100) if detection_count > 0 else 0
        
        logger.info(f"--- 处理进度 ---")
        logger.info(f"已处理图片: {image_count}")
        logger.info(f"检测总数: {detection_count}")
        logger.info(f"边缘检测数: {edge_detection_count} ({edge_ratio:.1f}%)")
        logger.info(f"平均每张检测数: {avg_detections:.2f}")
        logger.info(f"处理速度: {fps:.2f} 图片/秒")
    
    def _print_stats(self):
        """打印最终统计信息"""
        logger.info("\n" + "="*50)
        logger.info("处理统计信息")
        logger.info("="*50)
        
        self.synchronizer.print_stats()
        self.detector.print_stats()
        self.report_gen.print_stats()
        
        logger.info("="*50)
