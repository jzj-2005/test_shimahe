"""
GeoJSON导出模块
将CSV检测结果转换为GeoJSON格式用于GIS展示

坐标系：CGCS2000 (EPSG:4490)
格式：GeoJSON FeatureCollection
几何类型：Polygon（检测框四角点）
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd
from loguru import logger


class GeoJSONWriter:
    """GeoJSON写入器类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化GeoJSON写入器
        
        Args:
            config: 输出配置字典
        """
        self.config = config
        
        # 输出目录
        self.output_dir = config.get('geojson_dir', './data/output/geojson/')
        
        # 置信度阈值
        self.min_confidence = config.get('geojson_min_confidence', 0.0)
        self.high_confidence = config.get('geojson_high_confidence', 0.7)
        
        # 类别过滤（None表示不过滤）
        self.class_filter = config.get('geojson_class_filter', None)
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info(f"GeoJSON写入器初始化: 输出目录={self.output_dir}")
    
    def export_from_csv(self, csv_path: str) -> Dict[str, str]:
        """
        从CSV文件导出GeoJSON
        
        Args:
            csv_path: CSV文件路径
            
        Returns:
            导出的文件路径字典 {'raw': path1, 'unique': path2, ...}
        """
        try:
            df = pd.read_csv(csv_path)
            logger.info(f"读取CSV文件: {csv_path}, {len(df)} 条记录")
            return self.export_from_dataframe(df, df)  # 原始和去重相同
        except Exception as e:
            logger.error(f"读取CSV文件失败: {e}")
            return {}
    
    def export_multiple(
        self,
        df_raw: pd.DataFrame,
        df_unique: pd.DataFrame,
        output_dir: str = None
    ) -> Dict[str, str]:
        """
        导出多个版本的GeoJSON文件
        
        Args:
            df_raw: 原始完整数据（未去重）
            df_unique: 去重后数据
            output_dir: 输出目录（可选，覆盖默认配置）
            
        Returns:
            导出的文件路径字典
        """
        if output_dir is None:
            output_dir = self.output_dir
        else:
            os.makedirs(output_dir, exist_ok=True)
        
        results = {}
        
        try:
            # 1. 导出原始完整数据
            raw_path = os.path.join(output_dir, 'detections_raw.geojson')
            count_raw = self._export_dataframe(
                df_raw, 
                raw_path, 
                min_confidence=self.min_confidence
            )
            results['raw'] = raw_path
            logger.info(f"✓ 导出原始GeoJSON: {raw_path} ({count_raw}条)")
            
            # 2. 导出去重后数据
            unique_path = os.path.join(output_dir, 'detections_unique.geojson')
            count_unique = self._export_dataframe(
                df_unique, 
                unique_path, 
                min_confidence=self.min_confidence
            )
            results['unique'] = unique_path
            logger.info(f"✓ 导出去重GeoJSON: {unique_path} ({count_unique}条)")
            
            # 3. 导出高置信度数据（基于去重后的数据）
            high_conf_path = os.path.join(output_dir, 'detections_high_conf.geojson')
            count_high = self._export_dataframe(
                df_unique, 
                high_conf_path, 
                min_confidence=self.high_confidence
            )
            results['high_conf'] = high_conf_path
            logger.info(f"✓ 导出高置信度GeoJSON: {high_conf_path} ({count_high}条)")
            
            return results
            
        except Exception as e:
            logger.error(f"导出GeoJSON失败: {e}")
            return results
    
    def _export_dataframe(
        self, 
        df: pd.DataFrame, 
        output_path: str,
        min_confidence: float = 0.0,
        class_filter: List[str] = None
    ) -> int:
        """
        将DataFrame导出为GeoJSON文件
        
        Args:
            df: 数据框
            output_path: 输出文件路径
            min_confidence: 最小置信度阈值
            class_filter: 类别过滤列表
            
        Returns:
            导出的记录数
        """
        # 过滤数据
        filtered_df = df.copy()
        
        if min_confidence > 0:
            filtered_df = filtered_df[filtered_df['confidence'] >= min_confidence]
        
        if class_filter:
            filtered_df = filtered_df[filtered_df['class_name'].isin(class_filter)]
        
        # 转换为GeoJSON Features
        features = []
        for _, row in filtered_df.iterrows():
            try:
                feature = self._detection_to_feature(row)
                features.append(feature)
            except Exception as e:
                logger.warning(f"跳过无效记录 (frame {row.get('frame_number', '?')}): {e}")
        
        # 构建FeatureCollection
        geojson = {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {
                    "name": "urn:ogc:def:crs:EPSG::4490"  # CGCS2000坐标系
                }
            },
            "features": features,
            "properties": {
                "total_detections": len(features),
                "source": "石马河四乱检测系统",
                "coordinate_system": "CGCS2000",
                "coordinate_note": "已从WGS84（无人机GPS）转换为CGCS2000（国家标准）",
                "epsg_code": "EPSG:4490",
                "min_confidence": min_confidence
            }
        }
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)
        
        return len(features)
    
    def _detection_to_feature(self, row: pd.Series) -> Dict[str, Any]:
        """
        将单条检测记录转换为GeoJSON Feature
        
        Args:
            row: DataFrame的一行
            
        Returns:
            GeoJSON Feature对象
        """
        # 提取四角点坐标构成多边形
        coordinates = [[
            [row['corner1_lon'], row['corner1_lat']],
            [row['corner2_lon'], row['corner2_lat']],
            [row['corner3_lon'], row['corner3_lat']],
            [row['corner4_lon'], row['corner4_lat']],
            [row['corner1_lon'], row['corner1_lat']]  # 闭合多边形
        ]]
        
        # 构建属性（包含所有有用信息）
        properties = {
            'frame_number': int(row['frame_number']),
            'timestamp': float(row.get('timestamp', 0)),
            'datetime': str(row.get('datetime', '')),
            'class_id': int(row['class_id']),
            'class_name': str(row['class_name']),
            'confidence': float(row['confidence']),
            'center_lat': float(row['center_lat']),
            'center_lon': float(row['center_lon']),
            'altitude': float(row['altitude']),
            'drone_lat': float(row['drone_lat']),
            'drone_lon': float(row['drone_lon']),
            'is_on_edge': bool(row.get('is_on_edge', False)),
            'edge_positions': str(row.get('edge_positions', '')),
            'image_path': str(row.get('image_path', ''))
        }
        
        # 添加GPS质量信息（如果有）
        if 'gps_quality' in row and pd.notna(row['gps_quality']):
            properties['gps_quality'] = str(row['gps_quality'])
        
        if 'positioning_state' in row and pd.notna(row['positioning_state']):
            properties['positioning_state'] = str(row['positioning_state'])
        
        if 'estimated_error' in row and pd.notna(row['estimated_error']):
            properties['estimated_error'] = float(row['estimated_error'])
        
        if 'gps_level' in row and pd.notna(row['gps_level']):
            properties['gps_level'] = int(row['gps_level'])
        
        if 'satellite_count' in row and pd.notna(row['satellite_count']):
            properties['satellite_count'] = int(row['satellite_count'])
        
        # 构建Feature
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": coordinates
            },
            "properties": properties
        }
        
        return feature
    
    def export_from_dataframe(
        self, 
        df: pd.DataFrame,
        df_unique: pd.DataFrame = None,
        output_path: str = None
    ) -> str:
        """
        从DataFrame导出单个GeoJSON文件
        
        Args:
            df: 数据框（原始或去重）
            df_unique: 未使用（保持接口兼容）
            output_path: 输出路径（可选）
            
        Returns:
            输出文件路径
        """
        if output_path is None:
            output_path = os.path.join(self.output_dir, 'detections.geojson')
        
        self._export_dataframe(df, output_path, self.min_confidence, self.class_filter)
        
        return output_path
