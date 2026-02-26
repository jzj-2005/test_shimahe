"""
相机模型
管理相机内参和外参
"""

import numpy as np
from typing import Dict, Any, Tuple
from loguru import logger


class CameraModel:
    """相机模型类"""
    
    def __init__(self, camera_config: Dict[str, Any]):
        """
        初始化相机模型
        
        Args:
            camera_config: 相机配置字典
        """
        self.config = camera_config
        
        # 解析相机参数
        self._parse_config()
    
    def _parse_config(self):
        """解析配置参数"""
        camera = self.config.get('camera', {})
        
        # 基本信息
        self.model_name = camera.get('model', 'Unknown')
        
        # 图像分辨率
        resolution = camera.get('resolution', {})
        self.image_width = resolution.get('width', 4032)  # 默认M4TD分辨率
        self.image_height = resolution.get('height', 3024)
        
        # 传感器尺寸 (mm)
        sensor_size = camera.get('sensor_size', {})
        self.sensor_width = sensor_size.get('width', 13.4)  # 默认1/1.3英寸传感器
        self.sensor_height = sensor_size.get('height', 9.6)
        
        # 焦距 (mm)
        self.focal_length = camera.get('focal_length', 7.0)  # 默认M4TD焦距
        
        # 主点坐标 (像素)
        principal_point = camera.get('principal_point', {})
        self.cx = principal_point.get('cx', self.image_width / 2)
        self.cy = principal_point.get('cy', self.image_height / 2)
        
        # 畸变系数
        distortion = camera.get('distortion', {})
        self.k1 = distortion.get('k1', 0.0)
        self.k2 = distortion.get('k2', 0.0)
        self.p1 = distortion.get('p1', 0.0)
        self.p2 = distortion.get('p2', 0.0)
        self.k3 = distortion.get('k3', 0.0)
        
        # 正射模式参数
        ortho_mode = self.config.get('orthogonal_mode', {})
        self.assume_vertical = ortho_mode.get('assume_vertical', True)
        self.use_attitude_correction = ortho_mode.get('use_attitude_correction', False)
        
        # 地球参数
        earth = self.config.get('earth', {})
        self.meters_per_degree_lat = earth.get('meters_per_degree_lat', 110540)
        self.meters_per_degree_lon = earth.get('meters_per_degree_lon', 111320)
        
        # 验证关键参数
        self._validate_params()
        
        logger.info(f"相机模型初始化完成: {self.model_name}")
        logger.info(f"分辨率: {self.image_width}x{self.image_height}")
        logger.info(f"传感器尺寸: {self.sensor_width}x{self.sensor_height}mm")
        logger.info(f"焦距: {self.focal_length}mm")
        logger.info(f"正射模式: 垂直假设={self.assume_vertical}, 姿态修正={self.use_attitude_correction}")
    
    def _validate_params(self):
        """验证相机参数的合理性"""
        issues = []
        
        # 检查分辨率
        if self.image_width <= 0 or self.image_height <= 0:
            issues.append(f"❌ 图像分辨率无效: {self.image_width}x{self.image_height}")
        
        # 检查传感器尺寸
        if self.sensor_width <= 0 or self.sensor_height <= 0:
            issues.append(f"❌ 传感器尺寸无效: {self.sensor_width}x{self.sensor_height}mm")
        
        # 检查焦距
        if self.focal_length <= 0:
            issues.append(f"❌ 焦距无效: {self.focal_length}mm")
        
        # 检查主点坐标是否在图像范围内
        if not (0 <= self.cx <= self.image_width):
            issues.append(f"⚠️ 主点X坐标超出图像范围: cx={self.cx}, width={self.image_width}")
        
        if not (0 <= self.cy <= self.image_height):
            issues.append(f"⚠️ 主点Y坐标超出图像范围: cy={self.cy}, height={self.image_height}")
        
        # 输出验证结果
        if issues:
            logger.warning("相机参数验证发现问题:")
            for issue in issues:
                logger.warning(f"  {issue}")
            logger.warning("请检查 config/camera_params.yaml 配置文件!")
        else:
            logger.info("✓ 相机参数验证通过")
    
    def calculate_gsd(self, altitude: float) -> Tuple[float, float]:
        """
        计算地面分辨率 (Ground Sample Distance)
        
        Args:
            altitude: 飞行高度 (米)
            
        Returns:
            (gsd_x, gsd_y) 地面分辨率 (米/像素)
        """
        # GSD = (传感器尺寸 × 高度) / (焦距 × 图像尺寸)
        gsd_x = (self.sensor_width * altitude) / (self.focal_length * self.image_width)
        gsd_y = (self.sensor_height * altitude) / (self.focal_length * self.image_height)
        
        return gsd_x, gsd_y
    
    def pixel_to_normalized(self, u: float, v: float) -> Tuple[float, float]:
        """
        像素坐标转归一化坐标
        
        Args:
            u: 像素x坐标
            v: 像素y坐标
            
        Returns:
            (x_normalized, y_normalized)
        """
        x_norm = (u - self.cx) / self.focal_length
        y_norm = (v - self.cy) / self.focal_length
        
        return x_norm, y_norm
    
    def get_intrinsic_matrix(self) -> np.ndarray:
        """
        获取相机内参矩阵
        
        Returns:
            3x3内参矩阵
        """
        K = np.array([
            [self.focal_length, 0, self.cx],
            [0, self.focal_length, self.cy],
            [0, 0, 1]
        ])
        
        return K
    
    def get_distortion_coeffs(self) -> np.ndarray:
        """
        获取畸变系数
        
        Returns:
            畸变系数数组 [k1, k2, p1, p2, k3]
        """
        return np.array([self.k1, self.k2, self.p1, self.p2, self.k3])
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取相机信息
        
        Returns:
            相机信息字典
        """
        return {
            'model': self.model_name,
            'resolution': (self.image_width, self.image_height),
            'sensor_size': (self.sensor_width, self.sensor_height),
            'focal_length': self.focal_length,
            'principal_point': (self.cx, self.cy),
            'assume_vertical': self.assume_vertical,
            'use_attitude_correction': self.use_attitude_correction
        }
    
    def print_info(self):
        """打印相机信息"""
        info = self.get_info()
        logger.info("=== 相机参数信息 ===")
        logger.info(f"型号: {info['model']}")
        logger.info(f"分辨率: {info['resolution'][0]}x{info['resolution'][1]}")
        logger.info(f"传感器尺寸: {info['sensor_size'][0]}x{info['sensor_size'][1]}mm")
        logger.info(f"焦距: {info['focal_length']}mm")
        logger.info(f"主点: ({info['principal_point'][0]:.1f}, {info['principal_point'][1]:.1f})")
        logger.info(f"假设垂直: {info['assume_vertical']}")
        logger.info(f"姿态修正: {info['use_attitude_correction']}")
