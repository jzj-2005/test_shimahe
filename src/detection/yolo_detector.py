"""
YOLO检测引擎
使用YOLOv11x模型进行目标检测
"""

import numpy as np
from typing import List, Dict, Any, Optional
from ultralytics import YOLO
from loguru import logger


class YOLODetector:
    """YOLO检测器类"""
    
    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        device: str = "cuda",
        half_precision: bool = False,
        imgsz: int = 640,
        class_names: Dict[int, str] = None,
        target_classes: List[int] = None,
        tracker_type: str = "bytetrack.yaml"
    ):
        """
        初始化YOLO检测器
        
        Args:
            model_path: 模型权重文件路径
            confidence_threshold: 置信度阈值
            iou_threshold: IoU阈值
            device: 推理设备 ("cuda" 或 "cpu")
            half_precision: 是否使用半精度推理
            imgsz: 模型输入图像尺寸
            class_names: 类别名称映射
            target_classes: 目标类别列表（如果为None则检测所有类别）
            tracker_type: 跟踪器类型 ("bytetrack.yaml" 或 "botsort.yaml")
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.half_precision = half_precision
        self.imgsz = imgsz
        self.class_names = class_names or {}
        self.target_classes = target_classes
        self.tracker_type = tracker_type
        
        # 加载模型
        self.model = None
        self._load_model()
        
        # 统计信息
        self.inference_count = 0
        self.total_detections = 0
    
    def _load_model(self):
        """加载YOLO模型"""
        try:
            logger.info(f"正在加载YOLO模型: {self.model_path}")
            
            # 兼容 PyTorch 2.6+ 的 weights_only 参数
            # 临时允许加载 ultralytics 模型（来自可信源）
            import torch
            if hasattr(torch.serialization, 'add_safe_globals'):
                # PyTorch 2.6+
                try:
                    from ultralytics.nn.tasks import DetectionModel
                    torch.serialization.add_safe_globals([DetectionModel])
                except:
                    pass
            
            self.model = YOLO(self.model_path)
            
            # 设置设备
            self.model.to(self.device)
            
            logger.info(f"YOLO模型加载成功，设备: {self.device}")
            
            # 打印模型信息
            if hasattr(self.model, 'names'):
                model_classes = self.model.names
                logger.info(f"模型类别数: {len(model_classes)}")
                
                # 如果没有自定义类别名称，使用模型自带的
                if not self.class_names:
                    self.class_names = model_classes
            
        except Exception as e:
            logger.error(f"加载YOLO模型失败: {e}")
            raise
    
    def detect(
        self,
        image: np.ndarray,
        return_type: str = "corners",
        check_edge: bool = False,
        edge_threshold: int = 50
    ) -> List[Dict[str, Any]]:
        """
        对图像进行目标检测
        
        Args:
            image: 输入图像 (BGR格式)
            return_type: 返回坐标类型 ("corners"=四角点, "xyxy"=左上右下)
            check_edge: 是否检查目标框是否在图片边缘
            edge_threshold: 边缘距离阈值（像素），默认50像素
            
        Returns:
            检测结果列表
        """
        if self.model is None:
            logger.error("模型未加载")
            return []
        
        # 调试：打印第一次推理的参数
        if not hasattr(self, '_debug_logged'):
            self._debug_logged = True
            logger.info(f"【检测器调试】置信度阈值: {self.confidence_threshold}")
            logger.info(f"【检测器调试】输入尺寸: {self.imgsz}")
            logger.info(f"【检测器调试】图片尺寸: {image.shape}")
        
        try:
            # 推理
            results = self.model(
                image,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                imgsz=self.imgsz,
                half=self.half_precision,
                verbose=False
            )
            
            self.inference_count += 1
            
            # 解析结果
            detections = []
            
            # 获取图片尺寸（用于边缘检测）
            img_height, img_width = image.shape[:2]
            
            for result in results:
                boxes = result.boxes
                
                if boxes is None or len(boxes) == 0:
                    continue
                
                # 获取检测框信息
                xyxy = boxes.xyxy.cpu().numpy()  # 边界框坐标
                confs = boxes.conf.cpu().numpy()  # 置信度
                classes = boxes.cls.cpu().numpy().astype(int)  # 类别ID
                
                for box_xyxy, conf, cls in zip(xyxy, confs, classes):
                    # 如果指定了目标类别，只保留目标类别
                    if self.target_classes is not None and cls not in self.target_classes:
                        continue
                    
                    # 构建检测结果
                    x1, y1, x2, y2 = box_xyxy
                    detection = {
                        'class_id': int(cls),
                        'class_name': self.class_names.get(cls, f"class_{cls}"),
                        'confidence': float(conf),
                    }
                    
                    # 根据返回类型添加坐标
                    if return_type == "corners":
                        # 转换为四角点坐标
                        detection['corners'] = [
                            (float(x1), float(y1)),  # 左上
                            (float(x2), float(y1)),  # 右上
                            (float(x2), float(y2)),  # 右下
                            (float(x1), float(y2))   # 左下
                        ]
                    else:
                        # 保留xyxy格式
                        detection['xyxy'] = box_xyxy.tolist()
                    
                    # 边缘检测标记
                    if check_edge:
                        edge_info = self._check_box_on_edge(
                            x1, y1, x2, y2,
                            img_width, img_height,
                            edge_threshold
                        )
                        detection['is_on_edge'] = edge_info['is_on_edge']
                        detection['edge_positions'] = edge_info['positions']
                    
                    detections.append(detection)
                
                self.total_detections += len(detections)
            
            logger.debug(f"检测到 {len(detections)} 个目标")
            
            return detections
            
        except Exception as e:
            logger.error(f"YOLO检测时发生错误: {e}")
            return []
    
    def detect_batch(
        self,
        images: List[np.ndarray],
        return_type: str = "corners",
        check_edge: bool = False,
        edge_threshold: int = 50
    ) -> List[List[Dict[str, Any]]]:
        """
        批量检测
        
        Args:
            images: 图像列表
            return_type: 返回坐标类型
            check_edge: 是否检查边缘
            edge_threshold: 边缘距离阈值
            
        Returns:
            检测结果列表的列表
        """
        all_detections = []
        
        for image in images:
            detections = self.detect(image, return_type, check_edge, edge_threshold)
            all_detections.append(detections)
        
        return all_detections
    
    def detect_with_tracking(
        self,
        image: np.ndarray,
        return_type: str = "corners",
        edge_threshold: int = 50
    ) -> List[Dict[str, Any]]:
        """
        带目标跟踪的检测，使用 model.track() 为每个目标分配持久 track_id。
        强制启用边缘检测以支持 TrackManager 质量评分。
        
        Args:
            image: 输入图像 (BGR格式)
            return_type: 返回坐标类型 ("corners"=四角点, "xyxy"=左上右下)
            edge_threshold: 边缘距离阈值（像素）
            
        Returns:
            检测结果列表，每个字典包含 track_id 字段
        """
        if self.model is None:
            logger.error("模型未加载")
            return []
        
        if not hasattr(self, '_track_debug_logged'):
            self._track_debug_logged = True
            logger.info(f"[Tracking] tracker={self.tracker_type}, "
                       f"conf={self.confidence_threshold}, imgsz={self.imgsz}")
        
        try:
            results = self.model.track(
                image,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                imgsz=self.imgsz,
                half=self.half_precision,
                persist=True,
                tracker=self.tracker_type,
                verbose=False
            )
            
            self.inference_count += 1
            detections = []
            img_height, img_width = image.shape[:2]
            
            for result in results:
                boxes = result.boxes
                if boxes is None or len(boxes) == 0:
                    continue
                
                xyxy = boxes.xyxy.cpu().numpy()
                confs = boxes.conf.cpu().numpy()
                classes = boxes.cls.cpu().numpy().astype(int)
                
                track_ids = None
                if boxes.id is not None:
                    track_ids = boxes.id.cpu().numpy().astype(int)
                
                for idx, (box_xyxy, conf, cls) in enumerate(zip(xyxy, confs, classes)):
                    if self.target_classes is not None and cls not in self.target_classes:
                        continue
                    
                    tid = int(track_ids[idx]) if track_ids is not None else None
                    if tid is None:
                        continue
                    
                    x1, y1, x2, y2 = box_xyxy
                    detection = {
                        'class_id': int(cls),
                        'class_name': self.class_names.get(cls, f"class_{cls}"),
                        'confidence': float(conf),
                        'track_id': tid,
                    }
                    
                    if return_type == "corners":
                        detection['corners'] = [
                            (float(x1), float(y1)),
                            (float(x2), float(y1)),
                            (float(x2), float(y2)),
                            (float(x1), float(y2))
                        ]
                    else:
                        detection['xyxy'] = box_xyxy.tolist()
                    
                    edge_info = self._check_box_on_edge(
                        x1, y1, x2, y2,
                        img_width, img_height,
                        edge_threshold
                    )
                    detection['is_on_edge'] = edge_info['is_on_edge']
                    detection['edge_positions'] = edge_info['positions']
                    
                    detections.append(detection)
                
                self.total_detections += len(detections)
            
            logger.debug(f"[Tracking] detected {len(detections)} targets with track_ids")
            return detections
            
        except Exception as e:
            logger.error(f"YOLO tracking detection error: {e}")
            return []
    
    def reset_tracker(self):
        """重置跟踪器状态（切换视频时调用）"""
        if self.model is not None:
            self.model.predictor = None
            logger.info("Tracker state reset")
    
    def _check_box_on_edge(
        self,
        x1: float, y1: float, x2: float, y2: float,
        img_width: int, img_height: int,
        threshold: int = 50
    ) -> Dict[str, Any]:
        """
        检查检测框是否在图片边缘
        
        Args:
            x1, y1, x2, y2: 检测框坐标
            img_width: 图片宽度
            img_height: 图片高度
            threshold: 边缘距离阈值（像素）
            
        Returns:
            边缘信息字典，包含 is_on_edge 和 positions
        """
        edge_positions = []
        
        # 检查上边缘
        if y1 < threshold:
            edge_positions.append("top")
        
        # 检查下边缘
        if y2 > img_height - threshold:
            edge_positions.append("bottom")
        
        # 检查左边缘
        if x1 < threshold:
            edge_positions.append("left")
        
        # 检查右边缘
        if x2 > img_width - threshold:
            edge_positions.append("right")
        
        is_on_edge = len(edge_positions) > 0
        
        return {
            'is_on_edge': is_on_edge,
            'positions': edge_positions
        }
    
    def get_class_name(self, class_id: int) -> str:
        """
        获取类别名称
        
        Args:
            class_id: 类别ID
            
        Returns:
            类别名称
        """
        return self.class_names.get(class_id, f"class_{class_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        avg_detections = self.total_detections / self.inference_count if self.inference_count > 0 else 0
        
        return {
            'inference_count': self.inference_count,
            'total_detections': self.total_detections,
            'avg_detections_per_frame': avg_detections,
            'model_path': self.model_path,
            'device': self.device,
            'confidence_threshold': self.confidence_threshold
        }
    
    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        logger.info("=== YOLO检测统计 ===")
        logger.info(f"推理次数: {stats['inference_count']}")
        logger.info(f"检测目标总数: {stats['total_detections']}")
        logger.info(f"平均每帧检测数: {stats['avg_detections_per_frame']:.2f}")
        logger.info(f"置信度阈值: {stats['confidence_threshold']}")
