"""
坐标转换模块
将像素坐标转换为地理坐标 (CGCS2000)

输入：无人机GPS坐标为WGS84（国际标准）
输出：检测目标坐标为CGCS2000（中国国家标准）
转换精度：优于0.1米
"""

import numpy as np
from typing import List, Tuple, Dict, Any
from math import cos, sin, radians, degrees
from loguru import logger
from .camera_model import CameraModel

try:
    from pyproj import Transformer
    PYPROJ_AVAILABLE = True
except ImportError:
    PYPROJ_AVAILABLE = False
    logger.warning("pyproj库未安装，坐标将保持WGS84格式。请运行: pip install pyproj>=3.6.0")


class CoordinateTransformer:
    """坐标转换器类
    
    功能：
    1. 像素坐标 → WGS84地理坐标（基于相机模型和无人机位姿）
    2. WGS84坐标 → CGCS2000坐标（国家标准转换）
    
    输入：无人机GPS为WGS84（来自DJI飞控）
    输出：检测目标坐标为CGCS2000（符合国家标准GB/T 18522-2020）
    """
    
    def __init__(self, camera_model: CameraModel):
        """
        初始化坐标转换器
        
        Args:
            camera_model: 相机模型实例
        """
        self.camera = camera_model
        
        # 初始化WGS84到CGCS2000的坐标转换器
        if PYPROJ_AVAILABLE:
            try:
                # EPSG:4326 = WGS84 地理坐标系
                # EPSG:4490 = CGCS2000 地理坐标系
                self.wgs84_to_cgcs2000 = Transformer.from_crs(
                    "EPSG:4326",  # 源坐标系：WGS84
                    "EPSG:4490",  # 目标坐标系：CGCS2000
                    always_xy=True  # 确保输入输出都是(经度,纬度)顺序
                )
                logger.info("坐标转换器初始化完成 (WGS84 → CGCS2000)")
                self.enable_cgcs2000 = True
            except Exception as e:
                logger.warning(f"CGCS2000转换器初始化失败: {e}，将保持WGS84格式")
                self.enable_cgcs2000 = False
        else:
            logger.warning("pyproj未安装，坐标将保持WGS84格式")
            self.enable_cgcs2000 = False
    
    def convert_wgs84_to_cgcs2000(
        self, 
        coords_wgs84: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        """
        将WGS84坐标批量转换为CGCS2000坐标
        
        Args:
            coords_wgs84: WGS84坐标列表 [(lat1, lon1), (lat2, lon2), ...]
                         注意：输入格式为(纬度, 经度)
        
        Returns:
            CGCS2000坐标列表 [(lat1, lon1), (lat2, lon2), ...]
            如果转换失败或未启用，返回原始WGS84坐标
        """
        if not self.enable_cgcs2000:
            return coords_wgs84
        
        coords_cgcs2000 = []
        
        try:
            for lat_wgs, lon_wgs in coords_wgs84:
                # pyproj的transform方法输入输出都是(经度, 纬度)顺序
                lon_cgcs, lat_cgcs = self.wgs84_to_cgcs2000.transform(lon_wgs, lat_wgs)
                coords_cgcs2000.append((lat_cgcs, lon_cgcs))
            
            return coords_cgcs2000
        
        except Exception as e:
            logger.error(f"坐标转换失败: {e}，返回WGS84坐标")
            return coords_wgs84
    
    def pixel_to_geo(
        self,
        pixel_coords: List[Tuple[float, float]],
        pose: Dict[str, Any]
    ) -> List[Tuple[float, float]]:
        """
        将像素坐标转换为地理坐标 (CGCS2000)
        
        流程：
        1. 根据相机模型和无人机位姿，计算像素对应的WGS84坐标
        2. 将WGS84坐标转换为CGCS2000坐标
        
        Args:
            pixel_coords: 像素坐标列表 [(u1, v1), (u2, v2), ...]
            pose: 位姿数据字典，包含 latitude, longitude, altitude (均为WGS84)
            
        Returns:
            地理坐标列表 [(lat1, lon1), (lat2, lon2), ...] (CGCS2000坐标系)
        """
        # 提取位姿信息（来自无人机GPS，为WGS84坐标）
        drone_lat = pose.get('latitude', 0)
        drone_lon = pose.get('longitude', 0)
        altitude = pose.get('altitude', 0)
        
        if altitude == 0:
            logger.warning("飞行高度为0，坐标转换可能不准确")
        
        # 计算地面分辨率
        gsd_x, gsd_y = self.camera.calculate_gsd(altitude)
        
        # 航向角：用于将图像坐标系偏移旋转到东-北坐标系
        # DJI yaw: 0=正北, 顺时针为正
        yaw_rad = radians(pose.get('yaw', 0))
        cos_yaw = cos(yaw_rad)
        sin_yaw = sin(yaw_rad)
        
        # 转换每个像素点为WGS84坐标
        geo_coords_wgs84 = []
        
        for u, v in pixel_coords:
            # 计算像素相对于图像中心的偏移
            delta_u = u - self.camera.cx
            delta_v = v - self.camera.cy
            
            # 转换为地面距离 (米)
            # 图像坐标系: X=右, Y=下（相对于图像顶部）
            dx_img = delta_u * gsd_x
            dy_img = -delta_v * gsd_y  # 取负号：图像Y向下 → 机体前方向上
            
            # 应用 yaw 旋转：图像坐标系 → 东-北坐标系 (ENU)
            # 当 yaw=0（朝北）时，图像X=东, 图像Y=北（无旋转）
            # 当 yaw=θ 时，需要旋转 θ 角
            east  =  dx_img * cos_yaw + dy_img * sin_yaw
            north = -dx_img * sin_yaw + dy_img * cos_yaw
            
            # 转换为经纬度偏移
            delta_lat = north / self.camera.meters_per_degree_lat
            delta_lon = east / (self.camera.meters_per_degree_lon * cos(radians(drone_lat)))
            
            # 计算目标WGS84地理坐标
            target_lat = drone_lat + delta_lat
            target_lon = drone_lon + delta_lon
            
            geo_coords_wgs84.append((target_lat, target_lon))
        
        # 转换为CGCS2000坐标系
        geo_coords_cgcs2000 = self.convert_wgs84_to_cgcs2000(geo_coords_wgs84)
        
        return geo_coords_cgcs2000
    
    def pixel_to_geo_with_attitude(
        self,
        pixel_coords: List[Tuple[float, float]],
        pose: Dict[str, Any]
    ) -> List[Tuple[float, float]]:
        """
        将像素坐标转换为地理坐标 (考虑姿态角修正)
        
        Args:
            pixel_coords: 像素坐标列表
            pose: 位姿数据字典，包含 latitude, longitude, altitude, yaw, pitch, roll (WGS84)
            
        Returns:
            地理坐标列表 (CGCS2000坐标系)
        """
        # TODO: 实现考虑姿态角的完整坐标转换
        # 这需要更复杂的3D几何变换
        
        # 提取姿态角
        yaw = pose.get('yaw', 0)
        pitch = pose.get('pitch', -90)  # 默认垂直向下
        roll = pose.get('roll', 0)
        
        # 如果pitch接近-90度（垂直向下），使用简化算法
        if abs(pitch + 90) < 5:
            return self.pixel_to_geo(pixel_coords, pose)
        
        # 否则需要完整的3D变换
        logger.warning("当前版本暂不支持非垂直拍摄的姿态修正，使用简化算法")
        return self.pixel_to_geo(pixel_coords, pose)
    
    def transform_detection(
        self,
        detection: Dict[str, Any],
        pose: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        转换检测结果的坐标
        
        Args:
            detection: 检测结果字典，包含 corners 字段
            pose: 位姿数据 (WGS84)
            
        Returns:
            添加了 geo_coords 字段的检测结果 (坐标为CGCS2000)
        """
        if 'corners' not in detection:
            logger.warning("检测结果缺少corners字段")
            return detection
        
        pixel_coords = detection['corners']
        
        # 根据配置选择转换方法
        if self.camera.use_attitude_correction:
            geo_coords = self.pixel_to_geo_with_attitude(pixel_coords, pose)
        else:
            geo_coords = self.pixel_to_geo(pixel_coords, pose)
        
        # 添加地理坐标到检测结果
        detection['geo_coords'] = geo_coords
        
        # 计算中心点地理坐标
        if len(geo_coords) >= 4:
            center_lat = sum(coord[0] for coord in geo_coords) / len(geo_coords)
            center_lon = sum(coord[1] for coord in geo_coords) / len(geo_coords)
            detection['center_geo'] = (center_lat, center_lon)
        
        return detection
    
    def transform_detections(
        self,
        detections: List[Dict[str, Any]],
        pose: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        批量转换检测结果的坐标
        
        Args:
            detections: 检测结果列表
            pose: 位姿数据
            
        Returns:
            转换后的检测结果列表
        """
        transformed = []
        
        for detection in detections:
            transformed_detection = self.transform_detection(detection, pose)
            transformed.append(transformed_detection)
        
        return transformed
    
    def validate_geo_coords(self, lat: float, lon: float) -> bool:
        """
        验证地理坐标是否合法
        
        Args:
            lat: 纬度
            lon: 经度
            
        Returns:
            是否合法
        """
        # 纬度范围: -90 到 90
        # 经度范围: -180 到 180
        return -90 <= lat <= 90 and -180 <= lon <= 180
    
    def calculate_distance(
        self,
        coord1: Tuple[float, float],
        coord2: Tuple[float, float]
    ) -> float:
        """
        计算两个地理坐标之间的近似距离 (米)
        使用简化的平面近似公式
        
        Args:
            coord1: 第一个坐标 (lat, lon)
            coord2: 第二个坐标 (lat, lon)
            
        Returns:
            距离 (米)
        """
        lat1, lon1 = coord1
        lat2, lon2 = coord2
        
        # 纬度差对应的距离
        dy = (lat2 - lat1) * self.camera.meters_per_degree_lat
        
        # 经度差对应的距离
        avg_lat = (lat1 + lat2) / 2
        dx = (lon2 - lon1) * self.camera.meters_per_degree_lon * cos(radians(avg_lat))
        
        # 欧氏距离
        distance = np.sqrt(dx**2 + dy**2)
        
        return distance
