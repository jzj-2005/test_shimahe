"""
数据同步模块
负责同步视频帧与位姿数据
"""

import numpy as np
from typing import Dict, List, Optional, Any
from collections import deque
from loguru import logger


class DataSynchronizer:
    """数据同步器类"""
    
    def __init__(
        self,
        sync_method: str = "timestamp",
        timestamp_tolerance: float = 100.0,  # 毫秒
        max_time_diff: float = 500.0,  # 毫秒
        buffer_size: int = None  # None表示不限制
    ):
        """
        初始化数据同步器
        
        Args:
            sync_method: 同步方法 ("timestamp" 或 "frame_number")
            timestamp_tolerance: 时间戳容差 (毫秒)
            max_time_diff: 最大时间差 (毫秒)
            buffer_size: 位姿数据缓冲区大小（None表示不限制，适用于离线处理）
        """
        self.sync_method = sync_method
        self.timestamp_tolerance = timestamp_tolerance
        self.max_time_diff = max_time_diff
        self.buffer_size = buffer_size
        
        # 位姿数据缓冲区（离线处理时不限制大小）
        if buffer_size is None:
            self.pose_buffer = deque()  # 无maxlen限制
        else:
            self.pose_buffer = deque(maxlen=buffer_size)
        
        # 统计信息
        self.stats = {
            'total_frames': 0,
            'matched_frames': 0,
            'unmatched_frames': 0,
            'avg_time_diff': 0.0
        }
    
    def add_pose(self, pose_data: Dict[str, Any]):
        """
        添加位姿数据到缓冲区
        
        Args:
            pose_data: 位姿数据字典，必须包含 'timestamp' 键
        """
        if 'timestamp' not in pose_data:
            logger.warning("位姿数据缺少timestamp字段")
            return
        
        self.pose_buffer.append(pose_data)
    
    def sync_frame_with_pose(
        self,
        frame_timestamp: float,
        frame_number: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        根据时间戳同步帧与位姿数据
        
        Args:
            frame_timestamp: 帧时间戳 (毫秒)
            frame_number: 帧号 (可选)
            
        Returns:
            匹配的位姿数据，如果没有匹配则返回None
        """
        self.stats['total_frames'] += 1
        
        if len(self.pose_buffer) == 0:
            logger.warning(f"位姿缓冲区为空，无法同步帧 {frame_number}")
            self.stats['unmatched_frames'] += 1
            return None
        
        if self.sync_method == "timestamp":
            return self._sync_by_timestamp(frame_timestamp)
        elif self.sync_method == "frame_number" and frame_number is not None:
            return self._sync_by_frame_number(frame_number)
        else:
            logger.error(f"不支持的同步方法: {self.sync_method}")
            return None
    
    def _sync_by_timestamp(self, frame_timestamp: float) -> Optional[Dict[str, Any]]:
        """
        基于时间戳的最近邻匹配
        
        Args:
            frame_timestamp: 帧时间戳 (毫秒)
            
        Returns:
            匹配的位姿数据
        """
        # 调试：打印第一次同步的详细信息
        if not hasattr(self, '_debug_printed'):
            self._debug_printed = True
            logger.info(f"【同步器调试】图片时间戳: {frame_timestamp}ms")
            logger.info(f"【同步器调试】位姿缓冲区大小: {len(self.pose_buffer)}")
            if self.pose_buffer:
                first_pose = list(self.pose_buffer)[0]
                logger.info(f"【同步器调试】第一个GPS时间戳: {first_pose['timestamp']}ms")
                logger.info(f"【同步器调试】时间差: {abs(first_pose['timestamp'] - frame_timestamp)/1000}秒")
        
        # 找到时间差最小的位姿数据
        min_diff = float('inf')
        best_pose = None
        
        for pose in self.pose_buffer:
            time_diff = abs(pose['timestamp'] - frame_timestamp)
            
            if time_diff < min_diff:
                min_diff = time_diff
                best_pose = pose
        
        # 检查时间差是否在容差范围内
        # 调试：打印容差检查信息
        if not hasattr(self, '_tolerance_logged'):
            self._tolerance_logged = True
            logger.info(f"【同步器调试】最小时间差: {min_diff:.2f}ms")
            logger.info(f"【同步器调试】容差阈值: {self.max_time_diff:.2f}ms")
            logger.info(f"【同步器调试】是否匹配: {min_diff <= self.max_time_diff}")
        
        if best_pose and min_diff <= self.max_time_diff:
            self.stats['matched_frames'] += 1
            self.stats['avg_time_diff'] = (
                (self.stats['avg_time_diff'] * (self.stats['matched_frames'] - 1) + min_diff) 
                / self.stats['matched_frames']
            )
            
            logger.debug(f"成功匹配位姿数据，时间差: {min_diff:.2f}ms")
            return best_pose
        else:
            self.stats['unmatched_frames'] += 1
            logger.warning(f"未找到匹配的位姿数据，最小时间差: {min_diff:.2f}ms")
            return None
    
    def _sync_by_frame_number(self, frame_number: int) -> Optional[Dict[str, Any]]:
        """
        基于帧号的匹配
        
        Args:
            frame_number: 帧号
            
        Returns:
            匹配的位姿数据
        """
        for pose in self.pose_buffer:
            if 'frame_number' in pose and pose['frame_number'] == frame_number:
                self.stats['matched_frames'] += 1
                logger.debug(f"成功匹配位姿数据，帧号: {frame_number}")
                return pose
        
        self.stats['unmatched_frames'] += 1
        logger.warning(f"未找到匹配的位姿数据，帧号: {frame_number}")
        return None
    
    def interpolate_pose(
        self,
        frame_timestamp: float,
        poses: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        线性插值位姿数据 (高级功能)
        
        Args:
            frame_timestamp: 帧时间戳
            poses: 位姿数据列表 (至少需要2个)
            
        Returns:
            插值后的位姿数据
        """
        if len(poses) < 2:
            logger.warning("插值需要至少2个位姿数据点")
            return None
        
        # 排序位姿数据
        sorted_poses = sorted(poses, key=lambda x: x['timestamp'])
        
        # 查找前后两个位姿
        before_pose = None
        after_pose = None
        
        for i, pose in enumerate(sorted_poses):
            if pose['timestamp'] <= frame_timestamp:
                before_pose = pose
            if pose['timestamp'] >= frame_timestamp and after_pose is None:
                after_pose = pose
                break
        
        # 如果找不到前后位姿，返回最近的
        if before_pose is None:
            return sorted_poses[0]
        if after_pose is None:
            return sorted_poses[-1]
        
        # 线性插值
        t1 = before_pose['timestamp']
        t2 = after_pose['timestamp']
        t = frame_timestamp
        
        # 插值比例
        ratio = (t - t1) / (t2 - t1) if t2 != t1 else 0
        
        # 创建插值后的位姿数据
        interpolated_pose = {
            'timestamp': frame_timestamp,
            'latitude': before_pose['latitude'] + ratio * (after_pose['latitude'] - before_pose['latitude']),
            'longitude': before_pose['longitude'] + ratio * (after_pose['longitude'] - before_pose['longitude']),
            'altitude': before_pose['altitude'] + ratio * (after_pose['altitude'] - before_pose['altitude']),
        }
        
        # 如果有姿态角，也进行插值
        if 'yaw' in before_pose and 'yaw' in after_pose:
            interpolated_pose['yaw'] = before_pose['yaw'] + ratio * (after_pose['yaw'] - before_pose['yaw'])
        if 'pitch' in before_pose and 'pitch' in after_pose:
            interpolated_pose['pitch'] = before_pose['pitch'] + ratio * (after_pose['pitch'] - before_pose['pitch'])
        if 'roll' in before_pose and 'roll' in after_pose:
            interpolated_pose['roll'] = before_pose['roll'] + ratio * (after_pose['roll'] - before_pose['roll'])
        
        logger.debug(f"插值位姿数据，时间: {frame_timestamp}, 比例: {ratio:.3f}")
        return interpolated_pose
    
    def clear_buffer(self):
        """清空位姿缓冲区"""
        self.pose_buffer.clear()
        logger.info("位姿缓冲区已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取同步统计信息
        
        Returns:
            统计信息字典
        """
        stats = self.stats.copy()
        if stats['total_frames'] > 0:
            stats['match_rate'] = stats['matched_frames'] / stats['total_frames'] * 100
        else:
            stats['match_rate'] = 0.0
        return stats
    
    def print_stats(self):
        """打印同步统计信息"""
        stats = self.get_stats()
        logger.info("=== 数据同步统计 ===")
        logger.info(f"总帧数: {stats['total_frames']}")
        logger.info(f"匹配帧数: {stats['matched_frames']}")
        logger.info(f"未匹配帧数: {stats['unmatched_frames']}")
        logger.info(f"匹配率: {stats['match_rate']:.2f}%")
        logger.info(f"平均时间差: {stats['avg_time_diff']:.2f}ms")
