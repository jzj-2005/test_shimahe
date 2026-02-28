"""
实时处理流程
处理RTSP视频流 + OSD位姿数据（支持HTTP / MQTT / 自动降级）
"""

import time
import threading
from typing import Optional, Dict, Any
from loguru import logger

from .utils.config_loader import ConfigLoader
from .utils.logger import setup_logger
from .utils.data_sync import DataSynchronizer
from .utils.visualizer import Visualizer

from .input.rtsp_stream_reader import RTSPStreamReader
from .input.mqtt_client import DJIMQTTClient
from .input.http_osd_client import HttpOsdClient
from .input.osd_ocr_reader import OSDOCRReader

from .detection.yolo_detector import YOLODetector
from .detection.track_manager import TrackManager
from .transform.camera_model import CameraModel
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
        
        # OSD数据源：根据 osd_source 配置初始化
        self.osd_source = self.realtime_config.get('osd_source', 'auto')
        self.http_client: Optional[HttpOsdClient] = None
        self.mqtt_client: Optional[DJIMQTTClient] = None
        self.active_pose_source: str = "none"
        self._http_consecutive_failures: int = 0
        self._http_max_failures: int = 30
        
        if self.osd_source in ('http', 'auto'):
            http_config = self.realtime_config.get('http_osd', {})
            self.http_client = HttpOsdClient(
                base_url=http_config.get('base_url', ''),
                api_path=http_config.get('api_path', '/satxspace-airspace/ai/getDrone'),
                dev_sn=http_config.get('dev_sn', ''),
                poll_interval=http_config.get('poll_interval', 0.1),
                request_timeout=http_config.get('request_timeout', 2),
                max_retry=http_config.get('max_retry', 3),
                pose_buffer_size=http_config.get('pose_buffer_size', 100),
            )
            logger.info(f"HTTP OSD客户端已创建 (base_url={http_config.get('base_url')})")
        
        if self.osd_source in ('mqtt', 'auto'):
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
            logger.info("MQTT客户端已创建")
        
        logger.info(f"OSD数据源模式: {self.osd_source}")
        
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
        
        tracking_config = self.yolo_config.get('tracking', {})
        self.tracking_enabled = tracking_config.get('enabled', False)
        
        self.detector = YOLODetector(
            model_path=model_config.get('path', './models/yolov11x.pt'),
            confidence_threshold=detection_config.get('confidence_threshold', 0.5),
            iou_threshold=detection_config.get('iou_threshold', 0.45),
            device=model_config.get('device', 'cuda'),
            half_precision=model_config.get('half_precision', False),
            class_names=classes_config.get('names', {}),
            target_classes=classes_config.get('target_classes'),
            tracker_type=tracking_config.get('tracker', 'bytetrack.yaml'),
            obb_mode=model_config.get('obb_mode', False)
        )
        
        # 目标跟踪管理器（延迟保存策略）
        self.track_manager = None
        if self.tracking_enabled:
            self.track_manager = TrackManager(tracking_config)
            logger.info(">> Tracking dedup enabled (deferred save)")
        
        # 坐标转换器（根据配置选择简化版或增强版）
        self.camera_model = CameraModel(self.camera_config)
        coord_config = self.camera_config.get('coordinate_transform', {})
        
        if coord_config.get('use_enhanced', False):
            # 使用增强版转换器
            from .transform.coord_transform_new import CoordinateTransformerEnhanced
            quality_config = coord_config.get('quality_control', {})
            self.transformer = CoordinateTransformerEnhanced(
                camera_model=self.camera_model,
                quality_config=quality_config
            )
            logger.info("✓ 使用增强版坐标转换器（3D姿态修正 + GPS质量控制）")
        else:
            # 使用简化版转换器
            from .transform.coord_transform import CoordinateTransformer
            self.transformer = CoordinateTransformer(self.camera_model)
            logger.info("✓ 使用简化版坐标转换器（垂直投影）")
        
        # 报告生成器（v2.1新增：支持后处理）
        output_config = self.realtime_config.get('output', {})
        self.report_gen = ReportGenerator(
            csv_path=output_config.get('csv_path', './data/output/csv/detections_realtime.csv'),
            image_dir=output_config.get('image_dir', './data/output/images/'),
            save_images=output_config.get('save_images', True),
            image_format=output_config.get('image_format', 'full'),
            image_quality=output_config.get('image_quality', 85),
            csv_write_mode=output_config.get('csv_write_mode', 'append'),
            post_process_config=output_config  # 传递完整配置以启用后处理
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
            # 1. 连接OSD数据源
            if not self._connect_osd_source():
                logger.error("所有OSD数据源连接失败，处理终止")
                return
            
            # 启动OSD数据同步线程
            osd_sync_thread = threading.Thread(target=self._osd_data_loop, daemon=True)
            osd_sync_thread.start()
            
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
    
    def _connect_osd_source(self) -> bool:
        """按osd_source策略连接数据源，返回是否成功"""
        if self.osd_source == 'http':
            logger.info("步骤1: 连接HTTP OSD接口")
            if self.http_client and self.http_client.connect():
                self.active_pose_source = "http"
                logger.info("HTTP OSD接口连接成功 (主数据源)")
                return True
            logger.error("HTTP OSD接口连接失败")
            return False
        
        if self.osd_source == 'mqtt':
            logger.info("步骤1: 连接MQTT服务器")
            if self.mqtt_client and self.mqtt_client.connect():
                self.active_pose_source = "mqtt"
                logger.info("MQTT连接成功 (主数据源)")
                return True
            logger.error("MQTT连接失败")
            return False
        
        # auto模式：HTTP优先 → MQTT备选
        logger.info("步骤1: 连接OSD数据源 (auto模式: HTTP优先)")
        
        if self.http_client and self.http_client.connect():
            self.active_pose_source = "http"
            logger.info("HTTP OSD接口连接成功 (主数据源)")
            # auto模式下同时尝试连接MQTT作为备选
            if self.mqtt_client:
                try:
                    if self.mqtt_client.connect(timeout=5):
                        logger.info("MQTT备选连接成功")
                    else:
                        logger.warning("MQTT备选连接失败，仅使用HTTP")
                except Exception as e:
                    logger.warning(f"MQTT备选连接异常: {e}，仅使用HTTP")
            return True
        
        logger.warning("HTTP OSD接口不可用，降级到MQTT")
        if self.mqtt_client and self.mqtt_client.connect():
            self.active_pose_source = "mqtt"
            logger.info("MQTT连接成功 (降级数据源)")
            return True
        
        logger.error("HTTP和MQTT均不可用")
        return False
    
    def _osd_data_loop(self):
        """OSD数据同步循环（后台线程），将位姿数据写入同步器"""
        while self.is_running:
            client = self.http_client if self.active_pose_source == "http" else self.mqtt_client
            if client:
                pose_buffer = client.get_pose_buffer()
                for pose in pose_buffer:
                    self.synchronizer.add_pose(pose)
            time.sleep(0.1)
    
    def _get_pose(self, frame=None, frame_count: int = 0, frame_timestamp: float = 0) -> tuple:
        """统一位姿获取：HTTP优先 → MQTT备选 → OCR兜底
        
        Returns:
            (pose, source) - pose为位姿字典或None，source为数据来源标识
        """
        # 1. 尝试主数据源
        if self.active_pose_source == "http" and self.http_client:
            pose = self.http_client.get_latest_pose()
            if pose is not None:
                self._http_consecutive_failures = 0
                return pose, "http"
            
            self._http_consecutive_failures += 1
            
            # auto模式下：HTTP连续失败则尝试MQTT
            if (self.osd_source == "auto"
                    and self._http_consecutive_failures >= self._http_max_failures
                    and self.mqtt_client):
                if self.mqtt_client.is_connected:
                    pose = self.mqtt_client.get_latest_pose()
                    if pose is not None:
                        if self._http_consecutive_failures == self._http_max_failures:
                            logger.warning("HTTP OSD连续无数据，已自动切换到MQTT")
                        return pose, "mqtt"
        
        elif self.active_pose_source == "mqtt" and self.mqtt_client:
            pose = self.mqtt_client.get_latest_pose()
            if pose is not None:
                return pose, "mqtt"
        
        # 2. OCR兜底
        if self.ocr_fallback_enabled and self.osd_reader and frame is not None:
            pose = self.osd_reader.extract_pose_from_frame(
                frame, frame_count, frame_timestamp
            )
            if pose is not None:
                return pose, "ocr"
        
        return None, "none"
    
    def _process_loop(self):
        """实时处理循环"""
        frame_count = 0
        fps_start_time = time.time()
        fps_frame_count = 0
        current_fps = 0
        
        perf_config = self.realtime_config.get('performance', {})
        stats_interval = perf_config.get('stats_interval', 10)
        last_stats_time = time.time()
        
        # 位姿来源统计
        source_counts: Dict[str, int] = {"http": 0, "mqtt": 0, "ocr": 0}
        
        while self.is_running:
            frame = self.stream_reader.get_frame()
            
            if frame is None:
                time.sleep(0.01)
                continue
            
            frame_timestamp = time.time() * 1000
            
            pose, source = self._get_pose(frame, frame_count, frame_timestamp)
            
            if pose is not None:
                source_counts[source] = source_counts.get(source, 0) + 1
            else:
                logger.debug("暂无位姿数据（所有来源均失败）")
                time.sleep(0.01)
                continue
            
            if self.tracking_enabled and self.track_manager:
                detections = self.detector.detect_with_tracking(frame)
                if detections:
                    self.track_manager.update(detections, frame, pose, frame_count)
                self.track_manager.flush_lost_tracks(
                    frame_count, self.transformer, self.report_gen
                )
            else:
                detections = self.detector.detect(frame)
                if detections:
                    detections = self.transformer.transform_detections(detections, pose)
                if detections:
                    self.report_gen.save_realtime(detections, frame, pose, frame_count)
            
            if self.visualizer:
                fps_frame_count += 1
                if fps_frame_count % 10 == 0:
                    elapsed = time.time() - fps_start_time
                    current_fps = fps_frame_count / elapsed if elapsed > 0 else 0
                
                key = self.visualizer.show(frame, detections, pose, frame_count, current_fps)
                
                if key == 27:
                    logger.info("用户按下ESC键，退出处理")
                    break
            
            frame_count += 1
            
            if time.time() - last_stats_time >= stats_interval:
                self._print_realtime_stats(current_fps, source_counts, frame_count)
                last_stats_time = time.time()
        
        logger.info(f"共处理 {frame_count} 帧")
        logger.info(f"位姿来源统计: HTTP {source_counts.get('http', 0)} 帧, "
                    f"MQTT {source_counts.get('mqtt', 0)} 帧, "
                    f"OCR {source_counts.get('ocr', 0)} 帧")
    
    def _print_realtime_stats(self, fps: float, source_counts: Dict[str, int] = None, total_frames: int = 0):
        """打印实时统计信息"""
        logger.info("--- 实时统计 ---")
        logger.info(f"处理速度: {fps:.2f} FPS | 主数据源: {self.active_pose_source}")
        
        if source_counts and total_frames > 0:
            parts = []
            for src in ("http", "mqtt", "ocr"):
                cnt = source_counts.get(src, 0)
                if cnt > 0:
                    pct = cnt / total_frames * 100
                    parts.append(f"{src.upper()} {pct:.1f}%")
            if parts:
                logger.info(f"位姿来源: {', '.join(parts)}")
        
        stream_stats = self.stream_reader.get_stats()
        logger.info(f"视频流: 已接收{stream_stats['total_frames']}帧, "
                   f"缓冲区{stream_stats['buffer_size']}, "
                   f"重连{stream_stats['reconnect_count']}次")
        
        if self.http_client:
            http_stats = self.http_client.get_stats()
            logger.info(f"HTTP OSD: 成功{http_stats['message_count']}次, "
                       f"错误{http_stats['error_count']}次, "
                       f"延迟{http_stats['last_latency_ms']}ms")
        
        if self.mqtt_client:
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
        
        # 断开HTTP OSD
        if self.http_client:
            self.http_client.disconnect()
        
        # 断开MQTT
        if self.mqtt_client:
            self.mqtt_client.disconnect()
        
        # 关闭可视化
        if self.visualizer:
            self.visualizer.close()
        
        # 刷写所有剩余跟踪目标
        if hasattr(self, 'track_manager') and self.track_manager:
            try:
                self.track_manager.flush_all(self.transformer, self.report_gen)
                self.track_manager.print_stats()
            except Exception as e:
                logger.warning(f"刷写跟踪缓冲时出错: {e}")
        
        # 打印最终统计
        logger.info("\n" + "="*50)
        logger.info("最终统计信息")
        logger.info("="*50)
        
        self.detector.print_stats()
        self.report_gen.print_stats()
        
        # 关闭报告生成器并触发后处理（v2.1新增）
        if self.report_gen:
            try:
                self.report_gen.close()
            except Exception as e:
                logger.warning(f"关闭报告生成器时出错: {e}")
        
        logger.info("="*50)
        logger.info("实时处理流程已结束")
    
    def stop(self):
        """停止处理"""
        self.is_running = False
