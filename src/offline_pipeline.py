"""
离线处理流程
处理本地视频文件 + SRT字幕
"""

import time
from typing import Optional
from tqdm import tqdm
from loguru import logger

from .utils.config_loader import ConfigLoader
from .utils.logger import setup_logger
from .utils.data_sync import DataSynchronizer
from .utils.visualizer import Visualizer

from .input.video_file_reader import VideoFileReader
from .input.srt_extractor import SRTExtractor
from .input.srt_parser import SRTParser
from .input.osd_ocr_reader import OSDOCRReader

from .detection.yolo_detector import YOLODetector
from .transform.camera_model import CameraModel
from .transform.coord_transform import CoordinateTransformer
from .output.report_generator import ReportGenerator


class OfflinePipeline:
    """离线处理流程类"""
    
    def __init__(self, config_dir: str = "./config"):
        """
        初始化离线处理流程
        
        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = config_dir
        self.config_loader = ConfigLoader(config_dir)
        
        # 加载配置
        self.offline_config = self.config_loader.load('offline_config')
        self.yolo_config = self.config_loader.load('yolo_config')
        self.camera_config = self.config_loader.load('camera_params')
        
        # 初始化日志
        log_config = self.offline_config.get('logging', {})
        setup_logger(
            log_level=log_config.get('level', 'INFO'),
            log_file=log_config.get('log_file') if log_config.get('save_to_file') else None
        )
        
        # 初始化组件
        self._init_components()
        
        logger.info("离线处理流程初始化完成")
    
    def _init_components(self):
        """初始化各个组件"""
        # SRT提取器
        srt_config = self.offline_config.get('srt_extraction', {})
        self.srt_extractor = SRTExtractor(
            ffmpeg_path=srt_config.get('ffmpeg_path', 'ffmpeg'),
            temp_dir=self.offline_config.get('input', {}).get('temp_dir', './data/temp/srt')
        )
        
        # SRT解析器
        self.srt_parser = SRTParser()
        
        # OCR读取器（备用）
        ocr_config = self.offline_config.get('ocr', {})
        self.osd_reader = None
        if ocr_config.get('enabled', True):
            try:
                self.osd_reader = OSDOCRReader(
                    roi_config=ocr_config.get('roi', {'x': 0, 'y': 0, 'width': 600, 'height': 300}),
                    cache_enabled=True,
                    frame_interval=ocr_config.get('frame_interval', 5),
                    use_gpu=ocr_config.get('use_gpu', False),
                    language=ocr_config.get('language', 'ch')
                )
            except Exception as e:
                logger.warning(f"OCR初始化失败，将无法使用OCR备用功能: {e}")
                self.osd_reader = None
        
        # 数据同步器
        sync_config = self.offline_config.get('data_sync', {})
        self.synchronizer = DataSynchronizer(
            sync_method=sync_config.get('sync_method', 'timestamp'),
            timestamp_tolerance=sync_config.get('timestamp_tolerance', 100.0)
        )
        
        # YOLO检测器
        model_config = self.yolo_config.get('model', {})
        detection_config = self.yolo_config.get('detection', {})
        classes_config = self.yolo_config.get('classes', {})
        
        self.detector = YOLODetector(
            model_path=model_config.get('path', './models/yolov11x.pt'),
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
        output_config = self.offline_config.get('output', {})
        self.report_gen = ReportGenerator(
            csv_path=output_config.get('csv_path', './data/output/csv/detections_offline.csv'),
            image_dir=output_config.get('image_dir', './data/output/images/'),
            save_images=output_config.get('save_images', True),
            image_format=output_config.get('image_format', 'full'),
            image_quality=output_config.get('image_quality', 90),
            csv_write_mode='overwrite'
        )
        
        # 可视化器
        viz_config = self.offline_config.get('visualization', {})
        self.visualizer = None
        if viz_config.get('realtime_display', False):
            self.visualizer = Visualizer(
                display_width=viz_config.get('display_width', 1280),
                display_height=viz_config.get('display_height', 720),
                box_color=tuple(viz_config.get('box_color', [0, 255, 0])),
                box_thickness=viz_config.get('box_thickness', 2)
            )
    
    def run(self, video_path: Optional[str] = None):
        """
        运行离线处理流程
        
        Args:
            video_path: 视频文件路径 (如果为None，从配置中读取)
        """
        # 获取视频路径
        if video_path is None:
            video_path = self.offline_config.get('input', {}).get('video_path')
        
        if not video_path:
            logger.error("未指定视频文件路径")
            return
        
        logger.info(f"开始处理视频: {video_path}")
        
        # 标记是否使用OCR模式
        use_ocr_mode = False
        
        try:
            # 1. 尝试提取或查找SRT文件
            logger.info("步骤1: 提取SRT字幕")
            srt_path = self.srt_extractor.get_or_extract(video_path)
            
            if srt_path:
                # 2. 解析SRT文件
                logger.info("步骤2: 解析SRT数据")
                pose_data = self.srt_parser.parse(srt_path)
                
                if pose_data:
                    # 将位姿数据添加到同步器
                    for pose in pose_data:
                        self.synchronizer.add_pose(pose)
                    logger.info(f"SRT模式: 已加载 {len(pose_data)} 条位姿数据")
                else:
                    logger.warning("SRT解析失败")
                    srt_path = None
            
            # 如果SRT不可用，尝试使用OCR
            if not srt_path:
                if self.osd_reader:
                    logger.info("SRT不可用，切换到OCR模式提取飞行数据")
                    use_ocr_mode = True
                else:
                    logger.error("SRT不可用且OCR未启用，处理终止")
                    logger.info("提示：在config/offline_config.yaml中启用OCR配置")
                    return
            
            # 3. 打开视频文件
            step_num = 3 if not use_ocr_mode else 2
            logger.info(f"步骤{step_num}: 打开视频文件")
            video_config = self.offline_config.get('video_processing', {})
            
            video_reader = VideoFileReader(
                video_path=video_path,
                frame_skip=video_config.get('frame_skip', 1),
                start_frame=video_config.get('start_frame', 0),
                end_frame=video_config.get('end_frame', 0)
            )
            
            if not video_reader.open():
                logger.error("无法打开视频文件")
                return
            
            # 4. 逐帧处理
            step_num = 4 if not use_ocr_mode else 3
            logger.info(f"步骤{step_num}: 开始逐帧处理")
            self._process_frames(video_reader, use_ocr_mode)
            
            # 5. 关闭资源
            video_reader.close()
            if self.visualizer:
                self.visualizer.close()
            
            # 6. 打印统计信息
            self._print_stats()
            
            logger.info("离线处理完成")
            
        except KeyboardInterrupt:
            logger.warning("处理被用户中断")
        except Exception as e:
            logger.error(f"处理过程中发生错误: {e}", exc_info=True)
        finally:
            # 关闭报告生成器（释放CSV文件句柄）
            if hasattr(self, 'report_gen') and self.report_gen:
                try:
                    self.report_gen.close()
                except Exception as e:
                    logger.warning(f"关闭报告生成器时出错: {e}")
            
            # 关闭可视化
            if self.visualizer:
                try:
                    self.visualizer.close()
                except Exception as e:
                    logger.warning(f"关闭可视化窗口时出错: {e}")
    
    def _process_frames(self, video_reader: VideoFileReader, use_ocr_mode: bool = False):
        """
        逐帧处理视频
        
        Args:
            video_reader: 视频读取器
            use_ocr_mode: 是否使用OCR模式提取位姿
        """
        show_progress = self.offline_config.get('video_processing', {}).get('show_progress', True)
        total_frames = video_reader.end_frame - video_reader.start_frame
        
        # 创建进度条
        pbar = tqdm(total=total_frames, desc="处理进度") if show_progress else None
        
        frame_count = 0
        fps_start_time = time.time()
        fps_frame_count = 0
        current_fps = 0
        
        while True:
            # 读取帧
            success, frame, metadata = video_reader.read()
            
            if not success or frame is None:
                break
            
            frame_number = metadata['frame_number']
            frame_timestamp = metadata['timestamp']
            
            # 获取位姿数据
            if use_ocr_mode:
                # OCR模式: 从当前帧提取位姿
                pose = self.osd_reader.extract_pose_from_frame(
                    frame, frame_number, frame_timestamp
                )
                if pose:
                    # 将OCR提取的位姿添加到同步器（用于后续可能的查询）
                    self.synchronizer.add_pose(pose)
            else:
                # SRT模式: 从同步器获取位姿
                pose = self.synchronizer.sync_frame_with_pose(frame_timestamp, frame_number)
            
            if pose is None:
                if use_ocr_mode:
                    logger.debug(f"帧 {frame_number} OCR未能提取位姿数据")
                else:
                    logger.warning(f"帧 {frame_number} 未找到匹配的位姿数据")
                if pbar:
                    pbar.update(1)
                continue
            
            # YOLO检测
            detections = self.detector.detect(frame)
            
            # 获取输出配置
            output_config = self.offline_config.get('output', {})
            save_only_with_detections = output_config.get('save_only_with_detections', False)
            
            # 只在有检测结果时进行后续处理
            if detections:
                # 坐标转换
                detections = self.transformer.transform_detections(detections, pose)
                
                # 保存结果（CSV + 图片）
                self.report_gen.save(detections, frame, pose, frame_number)
            elif not save_only_with_detections:
                # 如果配置为保存所有帧，即使无检测也可以记录
                # （当前配置下会跳过）
                pass
            
            # 可视化
            if self.visualizer:
                # 计算FPS
                fps_frame_count += 1
                if fps_frame_count % 10 == 0:
                    elapsed = time.time() - fps_start_time
                    current_fps = fps_frame_count / elapsed if elapsed > 0 else 0
                
                key = self.visualizer.show(frame, detections, pose, frame_number, current_fps)
                
                # 按ESC退出
                if key == 27:
                    logger.info("用户按下ESC键，退出处理")
                    break
            
            frame_count += 1
            if pbar:
                pbar.update(1)
        
        if pbar:
            pbar.close()
        
        logger.info(f"共处理 {frame_count} 帧")
    
    def _print_stats(self):
        """打印统计信息"""
        logger.info("\n" + "="*50)
        logger.info("处理统计信息")
        logger.info("="*50)
        
        self.synchronizer.print_stats()
        self.detector.print_stats()
        self.report_gen.print_stats()
        
        logger.info("="*50)
