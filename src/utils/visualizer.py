"""
可视化模块
用于实时显示检测结果和相关信息
"""

import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger


class Visualizer:
    """可视化工具类"""
    
    def __init__(
        self,
        window_name: str = "Drone Inspection",
        display_width: int = 1280,
        display_height: int = 720,
        box_color: Tuple[int, int, int] = (0, 255, 0),
        box_thickness: int = 6,
        font_scale: float = 1.2,
        font_thickness: int = 3
    ):
        """
        初始化可视化工具
        
        Args:
            window_name: 显示窗口名称
            display_width: 显示窗口宽度
            display_height: 显示窗口高度
            box_color: 检测框颜色 (BGR格式)
            box_thickness: 检测框线条粗细
            font_scale: 字体大小
            font_thickness: 字体粗细
        """
        self.window_name = window_name
        self.display_width = display_width
        self.display_height = display_height
        self.box_color = box_color
        self.box_thickness = box_thickness
        self.font_scale = font_scale
        self.font_thickness = font_thickness
        
        # 为不同类别定义颜色映射（BGR格式）
        self.class_colors = {
            'Water Bodies': (255, 200, 0),         # 浅蓝色 - 水体
            'Vegetation': (0, 255, 0),             # 绿色 - 植被
            'Mining Area': (255, 0, 0),            # 蓝色 - 采矿区
            'Debris': (0, 165, 255),               # 橙色 - 垃圾
            'Industrial Buildings': (128, 0, 128), # 深紫 - 工业建筑
            'Waterway Facilities': (255, 255, 0),  # 青色 - 水务设施
            'Hydraulic Controls': (203, 192, 255), # 粉色 - 水利控制
            'Residences': (0, 255, 255),           # 黄色 - 住宅
            'Sheds': (0, 255, 255),                # 黄色 - 棚子
            'Storage Zones': (255, 0, 255),        # 紫色 - 堆放区
            'Recreation Areas': (147, 20, 255),    # 粉红 - 娱乐区
            'default': (0, 255, 0)                 # 默认绿色
        }
        
        # 创建窗口
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, display_width, display_height)
        
        logger.info(f"可视化窗口已创建: {window_name}")
    
    def draw_detections(
        self,
        image: np.ndarray,
        detections: List[Dict[str, Any]],
        show_labels: bool = True,
        show_confidence: bool = True
    ) -> np.ndarray:
        """
        在图像上绘制检测结果
        
        Args:
            image: 输入图像
            detections: 检测结果列表
            show_labels: 是否显示类别标签
            show_confidence: 是否显示置信度
            
        Returns:
            绘制后的图像
        """
        # 复制图像以避免修改原图
        img = image.copy()
        
        for det in detections:
            # 获取检测框四角点坐标
            corners = det.get('corners', [])
            if len(corners) != 4:
                continue
            
            # 转换为整数坐标
            pts = np.array([[int(x), int(y)] for x, y in corners], dtype=np.int32)
            
            # 根据类别选择颜色
            class_name = det.get('class_name', 'default')
            color = self.class_colors.get(class_name, self.class_colors['default'])
            
            # 绘制矩形框
            cv2.polylines(img, [pts], isClosed=True, color=color, thickness=self.box_thickness)
            
            # 准备标签文本
            label_parts = []
            if show_labels and 'class_name' in det:
                label_parts.append(det['class_name'])
            if show_confidence and 'confidence' in det:
                label_parts.append(f"{det['confidence']:.2f}")
            
            # 绘制标签
            if label_parts:
                label = ' '.join(label_parts)
                
                # 获取文本大小
                (text_width, text_height), baseline = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, self.font_scale, self.font_thickness
                )
                
                # 计算标签背景位置
                x1, y1 = int(corners[0][0]), int(corners[0][1])
                
                # 在标签位置上方留出更多空间
                label_y_top = max(y1 - text_height - baseline - 10, text_height + baseline + 10)
                label_y_bottom = label_y_top + text_height + baseline + 10
                
                # 绘制标签背景（使用类别颜色）
                cv2.rectangle(
                    img,
                    (x1, label_y_top),
                    (x1 + text_width + 10, label_y_bottom),
                    color,
                    -1
                )
                
                # 绘制标签文本（白色，加粗）
                cv2.putText(
                    img,
                    label,
                    (x1 + 5, label_y_bottom - baseline - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    self.font_scale,
                    (255, 255, 255),
                    self.font_thickness
                )
        
        return img
    
    def draw_info_panel(
        self,
        image: np.ndarray,
        pose: Optional[Dict[str, Any]] = None,
        frame_number: Optional[int] = None,
        fps: Optional[float] = None,
        detection_count: Optional[int] = None
    ) -> np.ndarray:
        """
        在图像上绘制信息面板
        
        Args:
            image: 输入图像
            pose: 位姿数据
            frame_number: 帧号
            fps: 处理速度 (帧率)
            detection_count: 检测目标数量
            
        Returns:
            绘制后的图像
        """
        img = image.copy()
        h, w = img.shape[:2]
        
        # 准备信息文本
        info_lines = []
        
        if frame_number is not None:
            info_lines.append(f"Frame: {frame_number}")
        
        if fps is not None:
            info_lines.append(f"FPS: {fps:.1f}")
        
        if detection_count is not None:
            info_lines.append(f"Detections: {detection_count}")
        
        if pose:
            if 'latitude' in pose and 'longitude' in pose:
                info_lines.append(f"GPS: {pose['latitude']:.6f}, {pose['longitude']:.6f}")
            if 'altitude' in pose:
                info_lines.append(f"Alt: {pose['altitude']:.1f}m")
            if 'yaw' in pose:
                info_lines.append(f"Yaw: {pose['yaw']:.1f}°")
        
        # 绘制信息面板背景
        panel_height = len(info_lines) * 30 + 20
        cv2.rectangle(img, (10, 10), (350, 10 + panel_height), (0, 0, 0), -1)
        cv2.rectangle(img, (10, 10), (350, 10 + panel_height), (255, 255, 255), 2)
        
        # 绘制信息文本
        y_offset = 35
        for line in info_lines:
            cv2.putText(
                img,
                line,
                (20, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1
            )
            y_offset += 30
        
        return img
    
    def show(
        self,
        image: np.ndarray,
        detections: Optional[List[Dict[str, Any]]] = None,
        pose: Optional[Dict[str, Any]] = None,
        frame_number: Optional[int] = None,
        fps: Optional[float] = None,
        wait_key: int = 1
    ) -> int:
        """
        显示图像和检测结果
        
        Args:
            image: 输入图像
            detections: 检测结果列表
            pose: 位姿数据
            frame_number: 帧号
            fps: 处理速度
            wait_key: 等待按键时间 (毫秒)
            
        Returns:
            按键值
        """
        img = image.copy()
        
        # 绘制检测结果
        if detections:
            img = self.draw_detections(img, detections)
        
        # 绘制信息面板
        detection_count = len(detections) if detections else 0
        img = self.draw_info_panel(img, pose, frame_number, fps, detection_count)
        
        # 调整图像大小以适应显示窗口
        img = cv2.resize(img, (self.display_width, self.display_height))
        
        # 显示图像
        cv2.imshow(self.window_name, img)
        
        # 等待按键
        key = cv2.waitKey(wait_key)
        return key
    
    def close(self):
        """关闭显示窗口"""
        try:
            cv2.destroyAllWindows()
            logger.info(f"可视化窗口已关闭: {self.window_name}")
        except Exception as e:
            logger.debug(f"关闭窗口时出现异常（可忽略）: {e}")
    
    @staticmethod
    def close_all():
        """关闭所有显示窗口"""
        cv2.destroyAllWindows()
        logger.info("所有可视化窗口已关闭")
