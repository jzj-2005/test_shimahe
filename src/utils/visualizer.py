"""
可视化模块
用于实时显示检测结果和相关信息
支持中文标签渲染（基于 PIL）
"""

import os
import colorsys
import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
from PIL import Image, ImageDraw, ImageFont


_FONT_PATH_CACHE: Optional[str] = None
_PIL_FONT_CACHE: Dict[int, ImageFont.FreeTypeFont] = {}


def _find_font_path() -> Optional[str]:
    """查找系统中可用的中文字体路径"""
    global _FONT_PATH_CACHE
    if _FONT_PATH_CACHE is not None:
        return _FONT_PATH_CACHE

    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            _FONT_PATH_CACHE = path
            return path
    _FONT_PATH_CACHE = ""
    return None


def get_pil_font(size: int) -> ImageFont.FreeTypeFont:
    """获取指定大小的 PIL 字体（带缓存），支持中文"""
    if size in _PIL_FONT_CACHE:
        return _PIL_FONT_CACHE[size]

    font_path = _find_font_path()
    if font_path:
        try:
            font = ImageFont.truetype(font_path, size)
        except Exception:
            font = ImageFont.load_default()
    else:
        font = ImageFont.load_default()

    _PIL_FONT_CACHE[size] = font
    return font


class Visualizer:
    """可视化工具类，支持中文标签"""
    
    def __init__(
        self,
        window_name: str = "Drone Inspection",
        display_width: int = 1280,
        display_height: int = 720,
        box_color: Tuple[int, int, int] = (0, 255, 0),
        box_thickness: int = 2,
        font_size: Optional[int] = None
    ):
        """
        初始化可视化工具
        
        Args:
            window_name: 显示窗口名称
            display_width: 显示窗口宽度
            display_height: 显示窗口高度
            box_color: 检测框颜色 (BGR格式)
            box_thickness: 检测框线条粗细
            font_size: 标签字体像素大小，None 则根据图像尺寸自动计算
        """
        self.window_name = window_name
        self.display_width = display_width
        self.display_height = display_height
        self.box_color = box_color
        self.box_thickness = box_thickness
        self.font_size = font_size
        
        # 预定义类别颜色映射（BGR 格式），未命中时自动生成
        self.class_colors: Dict[str, Tuple[int, int, int]] = {
            'Water Bodies': (255, 200, 0),
            'Vegetation': (0, 255, 0),
            'Mining Area': (255, 0, 0),
            'Debris': (0, 165, 255),
            'Industrial Buildings': (128, 0, 128),
            'Waterway Facilities': (255, 255, 0),
            'Hydraulic Controls': (203, 192, 255),
            'Residences': (0, 255, 255),
            'Sheds': (0, 255, 255),
            'Storage Zones': (255, 0, 255),
            'Recreation Areas': (147, 20, 255),
            'default': (0, 255, 0),
        }
        
        # 创建窗口
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, display_width, display_height)
        
        logger.info(f"可视化窗口已创建: {window_name}")

    def _get_class_color(self, class_name: str) -> Tuple[int, int, int]:
        """获取类别颜色，对未知类别自动生成视觉上可区分的颜色"""
        if class_name in self.class_colors:
            return self.class_colors[class_name]
        hue = (hash(class_name) * 0.618033988749895) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, 0.8, 0.95)
        color = (int(b * 255), int(g * 255), int(r * 255))
        self.class_colors[class_name] = color
        return color
    
    def draw_detections(
        self,
        image: np.ndarray,
        detections: List[Dict[str, Any]],
        show_labels: bool = True,
        show_confidence: bool = True
    ) -> np.ndarray:
        """
        在图像上绘制检测结果（使用 PIL 渲染文本以支持中文标签）
        """
        img = image.copy()
        h, w = img.shape[:2]
        
        font_size = self.font_size or max(round(max(h, w) / 150), 10)
        labels_to_draw = []
        
        for det in detections:
            corners = det.get('corners', [])
            if len(corners) != 4:
                continue
            
            pts = np.array([[int(x), int(y)] for x, y in corners], dtype=np.int32)
            class_name = det.get('class_name', 'default')
            color = self._get_class_color(class_name)
            
            cv2.polylines(img, [pts], isClosed=True, color=color, thickness=self.box_thickness)
            
            label_parts = []
            if show_labels and 'class_name' in det:
                label_parts.append(det['class_name'])
            if show_confidence and 'confidence' in det:
                label_parts.append(f"{det['confidence']:.2f}")
            
            if label_parts:
                label = ' '.join(label_parts)
                top_corner = min(corners, key=lambda c: c[1])
                x, y = int(top_corner[0]), int(top_corner[1])
                labels_to_draw.append((label, x, y, color))
        
        if labels_to_draw:
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_img)
            font = get_pil_font(font_size)
            pad = max(font_size // 6, 2)
            
            for label, x, y, color_bgr in labels_to_draw:
                color_rgb = (color_bgr[2], color_bgr[1], color_bgr[0])
                text_y = max(0, y - font_size - pad * 2)
                bbox = draw.textbbox((x, text_y), label, font=font)
                draw.rectangle(
                    [bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad],
                    fill=color_rgb
                )
                draw.text((x, text_y), label, font=font, fill=(255, 255, 255))
            
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        
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
