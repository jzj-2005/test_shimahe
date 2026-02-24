"""
实时处理流程
处理RTSP视频流 + MQTT位姿数据
"""

import time
import threading
from loguru import logger

from .utils.config_loader import ConfigLoader
from .utils.logger import setup_logger
from .utils.data_sync import DataSynchronizer
from .utils.visualizer import Visualizer

from .input.rtsp_stream_reader import RTSPStreamReader
from .input.mqtt_client import DJIMQTTClient
from .input.osd_ocr_reader import OSDOCRReader

from .detection.yolo_detector import YOLODetector
from .transform.camera_model import CameraModel
from .transform.coord_transform import CoordinateTransformer
from .output.report_generator import ReportGenerator


class RealtimePipeline:
    """实时处理流程类"""
    
    def __init__(self, config_dir: str = "./config"):
        """
        初始化实时处理流程
        
        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = config_dir
        self.config_loader = ConfigLoader(config_dir)
        
        # 加载配置
        self.realtime_config = self.config_loader.load('realtime_config')
        self.yolo_config = self.config_loader.load('yolo_config')
        self.camera_config = self.config_loader.load('camera_params')
        
        # 初始化日志
        log_config = self.realtime_config.get('logging', {})
        setup_logger(
            log_level=log_config.get('level', 'INFO'),
            log_file=log_config.get('log_file') if log_config.get('save_to_file') else None
        )
        
        # 运行状态
        self.is_running = False
        
        # 初始化组件
        self._init_components()
        
        logger.info("实时处理流程初始化完成")
    
    def _init_components(self):
        """初始化各个组件"""
        # RTSP流读取器
        rtsp_config = self.realtime_config.get('rtsp', {})
        self.stream_reader = RTSPStreamReader(
            rtsp_url=rtsp_config.get('url'),
            buffer_size=rtsp_config.get('buffer_size', 30),
            reconnect_interval=rtsp_config.get('reconnect_interval', 5),
            max_reconnect_attempts=rtsp_config.get('max_reconnect_attempts', 0),
            transport_protocol=rtsp_config.get('transport_protocol', 'tcp')
        )
        
        # MQTT客户端
        mqtt_config = self.realtime_config.get('mqtt', {})
        self.mqtt_client = DJIMQTTClient(
            broker=mqtt_config.get('broker'),
            port=mqtt_config.get('port', 1883),
            username=mqtt_config.get('username', ''),
            password=mqtt_config.get('password', ''),
            client_id=mqtt_config.get('client_id', 'drone_inspection_client'),
            topics=mqtt_config.get('topics', {}),
            qos=mqtt_config.get('qos', 1),
            keep_alive=mqtt_config.get('keep_alive', 60),
            pose_buffer_size=mqtt_config.get('pose_buffer_size', 100)
        )
        
        # 数据同步器
        sync_config = self.realtime_config.get('data_sync', {})
        self.synchronizer = DataSynchronizer(
            sync_method='timestamp',
            max_time_diff=sync_config.get('max_time_diff', 500.0)
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
            class_names=classes_config.get('names', {}),
            target_classes=classes_config.get('target_classes')
        )
        
        # 坐标转换器
        self.camera_model = CameraModel(self.camera_config)
        self.transformer = CoordinateTransformer(self.camera_model)
        
        # 报告生成器
        output_config = self.realtime_config.get('output', {})
        self.report_gen = ReportGenerator(
            csv_path=output_config.get('csv_path', './data/output/csv/detections_realtime.csv'),
            image_dir=output_config.get('image_dir', './data/output/images/'),
            save_images=output_config.get('save_images', True),
            image_format=output_config.get('image_format', 'full'),
            image_quality=output_config.get('image_quality', 85),
            csv_write_mode=output_config.get('csv_write_mode', 'append')
        )
        
        # 可视化器
        viz_config = self.realtime_config.get('visualization', {})
        self.visualizer = None
        if viz_config.get('realtime_display', False):
            self.visualizer = Visualizer(
                display_width=viz_config.get('display_width', 1280),
                display_height=viz_config.get('display_height', 720),
                box_color=tuple(viz_config.get('box_color', [0, 255, 0])),
                box_thickness=viz_config.get('box_thickness', 2)
            )
        
        # OCR备用读取器
        ocr_config = self.realtime_config.get('ocr_fallback', {})
        self.osd_reader = None
        self.ocr_fallback_enabled = ocr_config.get('enabled', True)
        if self.ocr_fallback_enabled:
            try:
                self.osd_reader = OSDOCRReader(
                    roi_config=ocr_config.get('roi', {'x': 0, 'y': 0, 'width': 600, 'height': 300}),
                    cache_enabled=True,
                    frame_interval=ocr_config.get('frame_interval', 10),  # 实时模式间隔更大
                    use_gpu=ocr_config.get('use_gpu', False),
                    language=ocr_config.get('language', 'ch')
                )
                logger.info("OCR备用功能已启用")
            except Exception as e:
                logger.warning(f"OCR初始化失败，将无法使用OCR备用功能: {e}")
                self.osd_reader = None
                self.ocr_fallback_enabled = False
    
    def run(self):
        """运行实时处理流程"""
        logger.info("启动实时处理流程")
        
        try:
            # 1. 连接MQTT服务器
            logger.info("步骤1: 连接MQTT服务器")
            if not self.mqtt_client.connect():
                logger.error("MQTT连接失败，处理终止")
                return
            
            # 启动MQTT数据接收线程
            mqtt_thread = threading.Thread(target=self._mqtt_data_loop, daemon=True)
            mqtt_thread.start()
            
            # 2. 启动RTSP流读取
            logger.info("步骤2: 启动RTSP流读取")
            self.stream_reader.start()
            
            # 等待流启动
            time.sleep(2)
            
            # 3. 开始处理循环
            logger.info("步骤3: 开始实时处理")
            self.is_running = True
            self._process_loop()
            
        except KeyboardInterrupt:
            logger.warning("处理被用户中断")
        except Exception as e:
            logger.error(f"处理过程中发生错误: {e}", exc_info=True)
        finally:
            self._cleanup()
    
    def _mqtt_data_loop(self):
        """MQTT数据接收循环（后台线程）"""
        while self.is_running:
            # 获取位姿数据缓冲区
            pose_buffer = self.mqtt_client.get_pose_buffer()
            
            # 添加到同步器
            for pose in pose_buffer:
                self.synchronizer.add_pose(pose)
            
            time.sleep(0.1)
    
    def _process_loop(self):
        """实时处理循环"""
        frame_count = 0
        fps_start_time = time.time()
        fps_frame_count = 0
        current_fps = 0
        
        perf_config = self.realtime_config.get('performance', {})
        stats_interval = perf_config.get('stats_interval', 10)
        last_stats_time = time.time()
        
        # OCR备用统计
        ocr_fallback_count = 0
        mqtt_success_count = 0
        
        while self.is_running:
            # 获取最新帧
            frame = self.stream_reader.get_frame()
            
            if frame is None:
                time.sleep(0.01)
                continue
            
            frame_timestamp = time.time() * 1000  # 毫秒
            
            # 优先从MQTT获取位姿数据
            pose = self.mqtt_client.get_latest_pose()
            
            if pose is not None:
                mqtt_success_count += 1
            elif self.ocr_fallback_enabled and self.osd_reader:
                # MQTT无数据，使用OCR备用
                pose = self.osd_reader.extract_pose_from_frame(
                    frame, frame_count, frame_timestamp
                )
                if pose:
                    ocr_fallback_count += 1
                    logger.debug(f"帧 {frame_count}: 使用OCR备用提取位姿")
            
            if pose is None:
                logger.debug("暂无位姿数据（MQTT和OCR均失败）")
                time.sleep(0.01)
                continue
            
            # YOLO检测
            detections = self.detector.detect(frame)
            
            # 坐标转换
            if detections:
                detections = self.transformer.transform_detections(detections, pose)
            
            # 保存结果
            if detections:
                self.report_gen.save_realtime(detections, frame, pose, frame_count)
            
            # 可视化
            if self.visualizer:
                # 计算FPS
                fps_frame_count += 1
                if fps_frame_count % 10 == 0:
                    elapsed = time.time() - fps_start_time
                    current_fps = fps_frame_count / elapsed if elapsed > 0 else 0
                
                key = self.visualizer.show(frame, detections, pose, frame_count, current_fps)
                
                # 按ESC退出
                if key == 27:
                    logger.info("用户按下ESC键，退出处理")
                    break
            
            frame_count += 1
            
            # 定期打印统计信息
            if time.time() - last_stats_time >= stats_interval:
                self._print_realtime_stats(current_fps, mqtt_success_count, ocr_fallback_count, frame_count)
                last_stats_time = time.time()
        
        logger.info(f"共处理 {frame_count} 帧")
        if self.ocr_fallback_enabled:
            logger.info(f"MQTT提供位姿: {mqtt_success_count} 帧, OCR备用: {ocr_fallback_count} 帧")
    
    def _print_realtime_stats(self, fps: float, mqtt_count: int = 0, ocr_count: int = 0, total_frames: int = 0):
        """打印实时统计信息"""
        logger.info("--- 实时统计 ---")
        logger.info(f"处理速度: {fps:.2f} FPS")
        
        if self.ocr_fallback_enabled and total_frames > 0:
            mqtt_pct = (mqtt_count / total_frames * 100) if total_frames > 0 else 0
            ocr_pct = (ocr_count / total_frames * 100) if total_frames > 0 else 0
            logger.info(f"位姿来源: MQTT {mqtt_pct:.1f}%, OCR {ocr_pct:.1f}%")
        
        stream_stats = self.stream_reader.get_stats()
        logger.info(f"视频流: 已接收{stream_stats['total_frames']}帧, "
                   f"缓冲区{stream_stats['buffer_size']}, "
                   f"重连{stream_stats['reconnect_count']}次")
        
        mqtt_stats = self.mqtt_client.get_stats()
        logger.info(f"MQTT: 已接收{mqtt_stats['message_count']}条消息, "
                   f"缓冲区{mqtt_stats['buffer_size']}, "
                   f"有位姿数据: {mqtt_stats['has_pose_data']}")
    
    def _cleanup(self):
        """清理资源"""
        logger.info("正在清理资源...")
        
        self.is_running = False
        
        # 停止RTSP流
        if self.stream_reader:
            self.stream_reader.stop()
        
        # 断开MQTT
        if self.mqtt_client:
            self.mqtt_client.disconnect()
        
        # 关闭可视化
        if self.visualizer:
            self.visualizer.close()
        
        # 打印最终统计
        logger.info("\n" + "="*50)
        logger.info("最终统计信息")
        logger.info("="*50)
        
        self.detector.print_stats()
        self.report_gen.print_stats()
        
        logger.info("="*50)
        logger.info("实时处理流程已结束")
    
    def stop(self):
        """停止处理"""
        self.is_running = False
