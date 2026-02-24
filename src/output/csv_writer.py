"""
CSV输出模块
将检测结果写入CSV文件

坐标系说明：
- 输出坐标系：CGCS2000 (EPSG:4490, 中国国家2000大地坐标系)
- 数据来源：DJI无人机GPS原始坐标为WGS84，已自动转换为CGCS2000
- 转换精度：优于0.1米
- 符合标准：GB/T 18522-2020《地理空间数据交换格式》
"""

import csv
import os
from typing import List, Dict, Any
from datetime import datetime
from loguru import logger


class CSVWriter:
    """
    CSV写入器类
    
    功能：将检测结果写入CSV文件
    
    输出坐标系：CGCS2000 (EPSG:4490)
    - corner1_lat/lon ~ corner4_lat/lon: 检测框四角点坐标 (CGCS2000)
    - center_lat/lon: 检测目标中心坐标 (CGCS2000)
    - drone_lat/lon: 无人机位置 (原始WGS84坐标，供参考)
    """
    
    def __init__(self, output_path: str, write_mode: str = "overwrite"):
        """
        初始化CSV写入器
        
        Args:
            output_path: CSV文件输出路径
            write_mode: 写入模式 ("overwrite" 或 "append")
        """
        self.output_path = output_path
        self.write_mode = write_mode
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # CSV字段名
        self.fieldnames = [
            'timestamp',
            'frame_number',
            'datetime',
            'class_id',
            'class_name',
            'confidence',
            'corner1_lat',
            'corner1_lon',
            'corner2_lat',
            'corner2_lon',
            'corner3_lat',
            'corner3_lon',
            'corner4_lat',
            'corner4_lon',
            'center_lat',
            'center_lon',
            'altitude',
            'drone_lat',
            'drone_lon',
            'is_on_edge',
            'edge_positions',
            'image_path'
        ]
        
        # 初始化文件
        self._init_file()
        
        self.write_count = 0
        self._file_handle = None
        self._csv_writer = None
        self._open_file_for_writing()
    
    def _init_file(self):
        """初始化CSV文件"""
        # 如果是覆盖模式或文件不存在，写入表头
        if self.write_mode == "overwrite" or not os.path.exists(self.output_path):
            try:
                with open(self.output_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                    writer.writeheader()
                
                logger.info(f"CSV文件已初始化: {self.output_path}")
            except Exception as e:
                logger.error(f"初始化CSV文件失败: {e}")
    
    def _open_file_for_writing(self):
        """打开文件用于持续写入"""
        try:
            self._file_handle = open(self.output_path, 'a', newline='', encoding='utf-8', buffering=1)
            self._csv_writer = csv.DictWriter(self._file_handle, fieldnames=self.fieldnames)
        except Exception as e:
            logger.error(f"打开CSV文件失败: {e}")
            self._file_handle = None
            self._csv_writer = None
    
    def write(
        self,
        detection: Dict[str, Any],
        pose: Dict[str, Any],
        frame_number: int,
        image_path: str = ""
    ):
        """
        写入单条检测记录
        
        Args:
            detection: 检测结果字典
            pose: 位姿数据字典
            frame_number: 帧号
            image_path: 图像路径
        """
        try:
            # 准备数据行
            row = {
                'timestamp': pose.get('timestamp', 0),
                'frame_number': frame_number,
                'datetime': pose.get('datetime', datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]),
                'class_id': detection.get('class_id', -1),
                'class_name': detection.get('class_name', 'unknown'),
                'confidence': detection.get('confidence', 0.0),
                'altitude': pose.get('altitude', 0.0),
                'drone_lat': pose.get('latitude', 0.0),
                'drone_lon': pose.get('longitude', 0.0),
                'image_path': image_path
            }
            
            # 添加四角点坐标
            geo_coords = detection.get('geo_coords', [])
            if len(geo_coords) >= 4:
                row['corner1_lat'] = geo_coords[0][0]
                row['corner1_lon'] = geo_coords[0][1]
                row['corner2_lat'] = geo_coords[1][0]
                row['corner2_lon'] = geo_coords[1][1]
                row['corner3_lat'] = geo_coords[2][0]
                row['corner3_lon'] = geo_coords[2][1]
                row['corner4_lat'] = geo_coords[3][0]
                row['corner4_lon'] = geo_coords[3][1]
            else:
                row['corner1_lat'] = row['corner1_lon'] = 0
                row['corner2_lat'] = row['corner2_lon'] = 0
                row['corner3_lat'] = row['corner3_lon'] = 0
                row['corner4_lat'] = row['corner4_lon'] = 0
            
            # 添加中心点坐标
            center_geo = detection.get('center_geo', (0, 0))
            row['center_lat'] = center_geo[0]
            row['center_lon'] = center_geo[1]
            
            # 添加边缘标记信息
            row['is_on_edge'] = detection.get('is_on_edge', False)
            edge_positions = detection.get('edge_positions', [])
            row['edge_positions'] = ','.join(edge_positions) if edge_positions else ''
            
            # 写入文件（使用持久化的文件句柄）
            if self._csv_writer is not None:
                self._csv_writer.writerow(row)
                self._file_handle.flush()  # 立即刷新到磁盘
                self.write_count += 1
            else:
                logger.warning("CSV写入器未正确初始化，尝试重新打开文件")
                self._open_file_for_writing()
                if self._csv_writer is not None:
                    self._csv_writer.writerow(row)
                    self._file_handle.flush()
                    self.write_count += 1
            
        except Exception as e:
            logger.error(f"写入CSV记录失败: {e}")
    
    def write_batch(
        self,
        detections: List[Dict[str, Any]],
        pose: Dict[str, Any],
        frame_number: int,
        image_paths: List[str] = None
    ):
        """
        批量写入检测记录
        
        Args:
            detections: 检测结果列表
            pose: 位姿数据
            frame_number: 帧号
            image_paths: 图像路径列表
        """
        if image_paths is None:
            image_paths = [""] * len(detections)
        
        for i, detection in enumerate(detections):
            image_path = image_paths[i] if i < len(image_paths) else ""
            self.write(detection, pose, frame_number, image_path)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'output_path': self.output_path,
            'write_count': self.write_count,
            'file_exists': os.path.exists(self.output_path)
        }
    
    def close(self):
        """关闭CSV写入器，释放文件句柄"""
        try:
            if self._file_handle is not None:
                self._file_handle.flush()
                self._file_handle.close()
                self._file_handle = None
                self._csv_writer = None
                logger.info(f"CSV文件已关闭: {self.output_path}, 共写入 {self.write_count} 条记录")
        except Exception as e:
            logger.error(f"关闭CSV文件失败: {e}")
    
    def __del__(self):
        """析构函数，确保文件被关闭"""
        self.close()
    
    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        logger.info("=== CSV写入统计 ===")
        logger.info(f"输出文件: {stats['output_path']}")
        logger.info(f"写入记录数: {stats['write_count']}")
        logger.info(f"文件存在: {stats['file_exists']}")
