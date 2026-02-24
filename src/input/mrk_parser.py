"""
MRK文件解析器
解析DJI RTK的MRK文件，提取GPS轨迹点数据
MRK文件格式示例：
1	282401.669089	[2404]	   101,N	   107,E	   129,V	22.77995359,Lat	114.10089118,Lon	139.231,Ellh	0.002967, 0.003104, 0.007622	50,Q
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from loguru import logger


class MRKParser:
    """MRK文件解析器类"""
    
    def __init__(self):
        """初始化MRK解析器"""
        self.pose_data = []
        self.reference_date = None  # GPS周参考日期
    
    def parse(self, mrk_path: str, reference_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        解析MRK文件
        
        Args:
            mrk_path: MRK文件路径
            reference_date: GPS周参考日期（用于转换GPS周内秒为标准时间）
                          如果为None，尝试从文件名提取日期
            
        Returns:
            位姿数据列表
        """
        try:
            # 尝试从文件名提取日期 (DJI_YYYYMMDDHHMMSS_序号_D.MRK)
            if reference_date is None:
                reference_date = self._extract_date_from_filename(mrk_path)
            
            self.reference_date = reference_date
            
            with open(mrk_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            self.pose_data = []
            
            for line_num, line in enumerate(lines, 1):
                pose = self._parse_line(line, line_num)
                if pose:
                    self.pose_data.append(pose)
            
            logger.info(f"成功解析MRK文件: {mrk_path}, 共{len(self.pose_data)}条位姿数据")
            
            return self.pose_data
            
        except Exception as e:
            logger.error(f"解析MRK文件时发生错误: {e}")
            return []
    
    def _extract_date_from_filename(self, filename: str) -> Optional[datetime]:
        """
        从文件名提取日期
        
        Args:
            filename: 文件名，格式如 DJI_20260204142623_0002_D.MRK
            
        Returns:
            日期时间对象
        """
        try:
            # 提取YYYYMMDDHHMMSS
            match = re.search(r'DJI_(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})', filename)
            if match:
                year, month, day, hour, minute, second = map(int, match.groups())
                date = datetime(year, month, day, hour, minute, second)
                logger.debug(f"从文件名提取日期: {date}")
                return date
        except Exception as e:
            logger.warning(f"无法从文件名提取日期: {e}")
        
        return None
    
    def _parse_line(self, line: str, line_num: int) -> Optional[Dict[str, Any]]:
        """
        解析MRK文件的单行
        
        MRK格式示例：
        1	282401.669089	[2404]	   101,N	   107,E	   129,V	22.77995359,Lat	114.10089118,Lon	139.231,Ellh	0.002967, 0.003104, 0.007622	50,Q
        
        字段说明：
        - 序号
        - GPS时间戳（周内秒）
        - [速度信息]
        - 速度分量（N/E/V）
        - 纬度,Lat
        - 经度,Lon
        - 椭球高度,Ellh
        - 精度信息（标准差）
        - 质量标志,Q
        
        Args:
            line: 文本行
            line_num: 行号
            
        Returns:
            位姿数据字典
        """
        try:
            line = line.strip()
            if not line:
                return None
            
            # 按制表符分割
            parts = line.split('\t')
            
            if len(parts) < 8:
                logger.debug(f"行 {line_num} 字段不足: {len(parts)}")
                return None
            
            # 解析序号
            sequence_num = int(parts[0])
            
            # 解析GPS时间戳（周内秒）
            gps_time_seconds = float(parts[1])
            
            # 转换为标准时间戳
            timestamp = self._convert_gps_time_to_timestamp(gps_time_seconds)
            
            # 提取纬度（查找包含"Lat"的字段）
            latitude = None
            longitude = None
            altitude = None
            
            for part in parts:
                if 'Lat' in part:
                    # 格式: "22.77995359,Lat"
                    lat_match = re.search(r'([-+]?\d+\.\d+),Lat', part)
                    if lat_match:
                        latitude = float(lat_match.group(1))
                
                elif 'Lon' in part:
                    # 格式: "114.10089118,Lon"
                    lon_match = re.search(r'([-+]?\d+\.\d+),Lon', part)
                    if lon_match:
                        longitude = float(lon_match.group(1))
                
                elif 'Ellh' in part:
                    # 格式: "139.231,Ellh"
                    alt_match = re.search(r'([-+]?\d+\.\d+),Ellh', part)
                    if alt_match:
                        altitude = float(alt_match.group(1))
            
            # 检查必需字段
            if latitude is None or longitude is None:
                logger.debug(f"行 {line_num} 缺少GPS坐标")
                return None
            
            # 构建位姿数据
            pose = {
                'sequence_num': sequence_num,
                'gps_time': gps_time_seconds,
                'timestamp': timestamp,
                'latitude': latitude,
                'longitude': longitude,
                'altitude': altitude if altitude is not None else 0.0,
                'line_num': line_num
            }
            
            # 解析速度信息（可选）
            if len(parts) >= 6:
                # 速度分量格式: "101,N", "107,E", "129,V"
                try:
                    vel_n_match = re.search(r'(\d+),N', parts[3])
                    vel_e_match = re.search(r'(\d+),E', parts[4])
                    vel_v_match = re.search(r'(\d+),V', parts[5])
                    
                    if vel_n_match:
                        pose['velocity_north'] = float(vel_n_match.group(1))
                    if vel_e_match:
                        pose['velocity_east'] = float(vel_e_match.group(1))
                    if vel_v_match:
                        pose['velocity_vertical'] = float(vel_v_match.group(1))
                except:
                    pass
            
            # 解析质量标志（可选）
            quality_match = re.search(r'(\d+),Q', parts[-1])
            if quality_match:
                pose['quality'] = int(quality_match.group(1))
            
            return pose
            
        except Exception as e:
            logger.debug(f"解析行 {line_num} 失败: {e}")
            return None
    
    def _convert_gps_time_to_timestamp(self, gps_seconds: float) -> float:
        """
        将GPS周内秒转换为时间戳（毫秒）
        
        Args:
            gps_seconds: GPS周内秒
            
        Returns:
            时间戳（毫秒）
        """
        if self.reference_date is None:
            # 如果没有参考日期，直接返回GPS秒数（作为相对时间）
            return gps_seconds * 1000
        
        try:
            # GPS周内秒转换为当天的秒数
            # GPS时间是UTC时间，从GPS周的周日0点开始计算
            seconds_in_day = gps_seconds % 86400  # 一天86400秒
            
            # reference_date 是从文件名提取的北京时间，需要转为UTC
            # 文件名: DJI_20260204142623 → 2026-02-04 14:26:23 北京时间
            # 转为UTC: 2026-02-04 06:26:23 UTC（减8小时）
            utc_reference = self.reference_date - timedelta(hours=8)
            
            # 计算GPS时间对应的UTC时刻（明确指定UTC时区）
            target_datetime = utc_reference.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            target_datetime += timedelta(seconds=seconds_in_day)
            
            # 转换为毫秒时间戳（UTC）
            timestamp = target_datetime.timestamp() * 1000
            
            return timestamp
            
        except Exception as e:
            logger.warning(f"GPS时间转换失败: {e}, 使用相对时间")
            return gps_seconds * 1000
    
    def get_pose_by_timestamp(self, timestamp: float, tolerance: float = 5000.0) -> Optional[Dict[str, Any]]:
        """
        根据时间戳获取位姿数据（最近邻匹配）
        
        Args:
            timestamp: 目标时间戳 (毫秒)
            tolerance: 容差 (毫秒)，默认5秒
            
        Returns:
            最接近的位姿数据
        """
        if not self.pose_data:
            return None
        
        # 找到时间差最小的位姿
        min_diff = float('inf')
        best_pose = None
        
        for pose in self.pose_data:
            diff = abs(pose['timestamp'] - timestamp)
            if diff < min_diff:
                min_diff = diff
                best_pose = pose
        
        # 检查是否在容差范围内
        if best_pose and min_diff <= tolerance:
            return best_pose
        
        return None
    
    def get_all_poses(self) -> List[Dict[str, Any]]:
        """
        获取所有位姿数据
        
        Returns:
            位姿数据列表
        """
        return self.pose_data
    
    def get_pose_count(self) -> int:
        """
        获取位姿数据总数
        
        Returns:
            数据总数
        """
        return len(self.pose_data)
    
    def print_sample(self, count: int = 5):
        """
        打印示例位姿数据
        
        Args:
            count: 打印数量
        """
        logger.info(f"=== MRK位姿数据示例 (前{count}条) ===")
        
        for i, pose in enumerate(self.pose_data[:count]):
            logger.info(f"[{i+1}] 序号: {pose.get('sequence_num', 'N/A')}, "
                       f"GPS时间: {pose.get('gps_time', 0):.2f}s, "
                       f"时间戳: {pose.get('timestamp', 0):.2f}ms, "
                       f"GPS: ({pose.get('latitude', 0):.8f}, {pose.get('longitude', 0):.8f}), "
                       f"高度: {pose.get('altitude', 0):.3f}m")
