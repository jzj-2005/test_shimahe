"""
智能去重模块
解决实时检测中的重复目标问题

功能：
1. 空间距离分组（基于GPS坐标）
2. 质量评分（综合置信度、边缘位置、GPS质量、定位误差）
3. 保留最佳检测（每组选择评分最高的）
"""

import math
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple
from loguru import logger


class DetectionDeduplicator:
    """检测结果去重器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化去重器
        
        Args:
            config: 去重配置字典
        """
        if config is None:
            config = {}
        
        # 距离阈值（米）：小于此距离视为同一目标
        self.distance_threshold = config.get('distance_threshold', 5.0)
        
        # 质量评分权重配置
        self.prefer_non_edge = config.get('prefer_non_edge', True)
        self.prefer_high_confidence = config.get('prefer_high_confidence', True)
        self.prefer_rtk = config.get('prefer_rtk', True)
        
        # 最低质量评分阈值
        self.min_quality_score = config.get('min_quality_score', 0.0)
        
        # 边缘惩罚系数
        self.edge_penalty = config.get('edge_penalty', 0.5)
        
        # GPS质量系数
        self.gps_quality_weights = {
            'RTK': 1.2,
            'HIGH': 1.0,
            'MEDIUM': 0.9,
            'LOW': 0.7,
            'INVALID': 0.5
        }
        
        logger.info(f"去重器初始化: 距离阈值={self.distance_threshold}米")
    
    def deduplicate_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        对DataFrame进行去重
        
        Args:
            df: 包含检测结果的DataFrame
            
        Returns:
            去重后的DataFrame
        """
        if len(df) == 0:
            logger.warning("输入数据为空，跳过去重")
            return df
        
        # 检查必要字段
        required_fields = ['center_lat', 'center_lon', 'confidence']
        missing_fields = [f for f in required_fields if f not in df.columns]
        if missing_fields:
            logger.error(f"缺少必要字段: {missing_fields}，跳过去重")
            return df
        
        logger.info(f"开始去重: {len(df)} 条记录")
        
        # 转换为字典列表
        detections = df.to_dict('records')
        
        # 添加索引（用于追溯原始行）
        for i, det in enumerate(detections):
            det['_original_index'] = i
        
        # 执行去重
        unique_detections = self.deduplicate(detections)
        
        # 提取保留的索引
        unique_indices = [det['_original_index'] for det in unique_detections]
        
        # 返回去重后的DataFrame
        df_unique = df.iloc[unique_indices].reset_index(drop=True)
        
        logger.info(f"去重完成: {len(df)} -> {len(df_unique)} 条 "
                   f"(去除 {len(df) - len(df_unique)} 条重复, "
                   f"去重率 {(len(df) - len(df_unique)) / len(df) * 100:.1f}%)")
        
        return df_unique
    
    def deduplicate(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        对检测列表进行去重
        
        Args:
            detections: 检测结果列表
            
        Returns:
            去重后的检测列表
        """
        if not detections:
            return []
        
        # 步骤1：计算质量评分
        for det in detections:
            det['_quality_score'] = self._calculate_quality_score(det)
        
        # 步骤2：过滤低质量检测
        if self.min_quality_score > 0:
            detections = [det for det in detections 
                         if det['_quality_score'] >= self.min_quality_score]
            logger.info(f"质量过滤后: {len(detections)} 条")
        
        # 步骤3：按空间距离分组
        groups = self._group_by_distance(detections)
        logger.info(f"空间分组: 发现 {len(groups)} 个位置聚类")
        
        # 步骤4：每组保留质量评分最高的
        unique_detections = []
        for group in groups:
            best_detection = max(group, key=lambda x: x['_quality_score'])
            # 移除临时字段
            best_detection.pop('_quality_score', None)
            unique_detections.append(best_detection)
        
        return unique_detections
    
    def _calculate_quality_score(self, detection: Dict[str, Any]) -> float:
        """
        计算检测质量评分
        
        考虑因素：
        1. 置信度（confidence）
        2. 是否在边缘（is_on_edge）
        3. GPS质量（gps_quality）
        4. 定位误差（estimated_error）
        
        Args:
            detection: 检测结果字典
            
        Returns:
            质量评分（0-2之间，越高越好）
        """
        # 基础评分：置信度
        score = detection.get('confidence', 0.0)
        
        # 因素1：边缘惩罚
        if self.prefer_non_edge:
            is_on_edge = detection.get('is_on_edge', False)
            if is_on_edge:
                score *= self.edge_penalty
        
        # 因素2：GPS质量加成
        if self.prefer_rtk:
            gps_quality = detection.get('gps_quality', 'MEDIUM')
            gps_weight = self.gps_quality_weights.get(gps_quality, 1.0)
            score *= gps_weight
        
        # 因素3：定位误差惩罚
        estimated_error = detection.get('estimated_error', 0.0)
        if estimated_error > 10.0:
            score *= 0.8
        elif estimated_error > 5.0:
            score *= 0.9
        
        return score
    
    def _group_by_distance(self, detections: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        按空间距离对检测进行分组
        
        使用贪心聚类算法：
        1. 遍历所有检测
        2. 对于每个检测，找到距离最近的已有组
        3. 如果距离 < threshold，加入该组；否则创建新组
        
        Args:
            detections: 检测结果列表
            
        Returns:
            分组后的检测列表
        """
        if not detections:
            return []
        
        groups = []
        
        for detection in detections:
            lat = detection.get('center_lat', 0.0)
            lon = detection.get('center_lon', 0.0)
            
            # 查找是否有相近的组
            found_group = False
            for group in groups:
                # 计算与组中任一成员的距离
                for member in group:
                    member_lat = member.get('center_lat', 0.0)
                    member_lon = member.get('center_lon', 0.0)
                    
                    distance = self._haversine_distance(
                        lat, lon, member_lat, member_lon
                    )
                    
                    if distance < self.distance_threshold:
                        group.append(detection)
                        found_group = True
                        break
                
                if found_group:
                    break
            
            # 如果没有找到相近的组，创建新组
            if not found_group:
                groups.append([detection])
        
        return groups
    
    def _haversine_distance(
        self, 
        lat1: float, 
        lon1: float, 
        lat2: float, 
        lon2: float
    ) -> float:
        """
        计算两个GPS坐标之间的地面距离（米）
        使用Haversine公式
        
        Args:
            lat1, lon1: 第一个点的纬度、经度
            lat2, lon2: 第二个点的纬度、经度
            
        Returns:
            距离（米）
        """
        # 地球半径（米）
        R = 6371000
        
        # 转换为弧度
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        # Haversine公式
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        
        return distance
    
    def get_deduplication_stats(
        self, 
        original_count: int, 
        unique_count: int
    ) -> Dict[str, Any]:
        """
        生成去重统计信息
        
        Args:
            original_count: 原始检测数量
            unique_count: 去重后数量
            
        Returns:
            统计信息字典
        """
        removed_count = original_count - unique_count
        removal_rate = (removed_count / original_count * 100) if original_count > 0 else 0
        
        return {
            'original_count': original_count,
            'unique_count': unique_count,
            'removed_count': removed_count,
            'removal_rate': removal_rate,
            'distance_threshold': self.distance_threshold,
            'edge_penalty': self.edge_penalty
        }


def visualize_deduplication(
    detections_before: List[Dict[str, Any]],
    detections_after: List[Dict[str, Any]]
) -> str:
    """
    可视化去重效果（用于调试和分析）
    
    Args:
        detections_before: 去重前的检测列表
        detections_after: 去重后的检测列表
        
    Returns:
        统计文本
    """
    stats = []
    stats.append(f"去重前: {len(detections_before)} 条检测")
    stats.append(f"去重后: {len(detections_after)} 条检测")
    stats.append(f"去除: {len(detections_before) - len(detections_after)} 条重复")
    stats.append(f"去重率: {(len(detections_before) - len(detections_after)) / len(detections_before) * 100:.1f}%")
    
    return "\n".join(stats)
