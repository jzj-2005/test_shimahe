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
    
    @staticmethod
    def _lerp_angle(a1: float, a2: float, ratio: float) -> float:
        """最短弧角度插值，正确处理 ±180° 边界"""
        diff = (a2 - a1 + 180) % 360 - 180
        return a1 + ratio * diff

    def _interpolate_field(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any],
        key: str,
        ratio: float,
        is_angle: bool = False,
        default: Any = None
    ) -> Any:
        """插值单个字段，缺失时取最近值或默认值"""
        v1 = before.get(key)
        v2 = after.get(key)
        if v1 is None and v2 is None:
            return default
        if v1 is None:
            return v2
        if v2 is None:
            return v1
        if is_angle:
            return self._lerp_angle(v1, v2, ratio)
        return v1 + ratio * (v2 - v1)

    def sync_frame_interpolated(
        self,
        frame_timestamp: float
    ) -> Optional[Dict[str, Any]]:
        """
        基于缓冲区的线性插值同步：找到帧时间戳前后的两条 OSD 数据做插值。
        如果缓冲区不足两条或时间差超限，回退到最近邻匹配。

        Args:
            frame_timestamp: 帧时间戳（毫秒）

        Returns:
            插值后的位姿数据，或 None
        """
        self.stats['total_frames'] += 1

        if len(self.pose_buffer) == 0:
            self.stats['unmatched_frames'] += 1
            return None

        # 只有 1 条数据时直接返回
        if len(self.pose_buffer) == 1:
            only = self.pose_buffer[0]
            if abs(only['timestamp'] - frame_timestamp) <= self.max_time_diff:
                self.stats['matched_frames'] += 1
                return dict(only)
            self.stats['unmatched_frames'] += 1
            return None

        # 在缓冲区中找前后两条（缓冲区按 add_pose 顺序，时间基本递增）
        before_pose = None
        after_pose = None
        for pose in self.pose_buffer:
            if pose['timestamp'] <= frame_timestamp:
                before_pose = pose
            else:
                after_pose = pose
                break

        # 边界情况：帧时间在所有数据之前或之后，回退到最近邻
        if before_pose is None:
            nearest = self.pose_buffer[0]
        elif after_pose is None:
            nearest = self.pose_buffer[-1]
        else:
            nearest = None

        if nearest is not None:
            if abs(nearest['timestamp'] - frame_timestamp) <= self.max_time_diff:
                self.stats['matched_frames'] += 1
                return dict(nearest)
            self.stats['unmatched_frames'] += 1
            return None

        # 时间差超限检查
        if (frame_timestamp - before_pose['timestamp'] > self.max_time_diff or
                after_pose['timestamp'] - frame_timestamp > self.max_time_diff):
            self.stats['unmatched_frames'] += 1
            return None

        # 插值比例
        t1 = before_pose['timestamp']
        t2 = after_pose['timestamp']
        ratio = (frame_timestamp - t1) / (t2 - t1) if t2 != t1 else 0.0

        # 需要线性插值的标量字段
        linear_fields = [
            'latitude', 'longitude', 'altitude',
            'relative_height', 'ground_speed', 'velocity_z',
        ]
        # 需要最短弧插值的角度字段
        angle_fields = [
            'yaw', 'pitch', 'roll',
            'gimbal_pitch', 'gimbal_yaw', 'gimbal_roll',
        ]
        # 不插值、直接取最近值的离散字段
        nearest_fields = [
            'satellite_count', 'gps_level', 'positioning_state',
            'battery_percent',
        ]

        result = {'timestamp': frame_timestamp}

        for key in linear_fields:
            val = self._interpolate_field(before_pose, after_pose, key, ratio)
            if val is not None:
                result[key] = val

        for key in angle_fields:
            val = self._interpolate_field(before_pose, after_pose, key, ratio, is_angle=True)
            if val is not None:
                result[key] = val

        for key in nearest_fields:
            closer = before_pose if ratio <= 0.5 else after_pose
            val = closer.get(key)
            if val is not None:
                result[key] = val

        # 保留 before_pose 中存在但未被插值覆盖的其他字段
        for key in before_pose:
            if key not in result:
                result[key] = before_pose[key]

        self.stats['matched_frames'] += 1
        time_diff = min(frame_timestamp - t1, t2 - frame_timestamp)
        self.stats['avg_time_diff'] = (
            (self.stats['avg_time_diff'] * (self.stats['matched_frames'] - 1) + time_diff)
            / self.stats['matched_frames']
        )

        logger.debug(f"插值位姿: ratio={ratio:.3f}, 前={t1:.0f}ms 后={t2:.0f}ms 帧={frame_timestamp:.0f}ms")
        return result

    def interpolate_pose(
        self,
        frame_timestamp: float,
        poses: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        从给定列表插值位姿数据（保留向后兼容，离线管线可用）
        """
        if len(poses) < 2:
            return poses[0] if poses else None

        sorted_poses = sorted(poses, key=lambda x: x['timestamp'])

        before_pose = None
        after_pose = None
        for pose in sorted_poses:
            if pose['timestamp'] <= frame_timestamp:
                before_pose = pose
            elif after_pose is None:
                after_pose = pose
                break

        if before_pose is None:
            return dict(sorted_poses[0])
        if after_pose is None:
            return dict(sorted_poses[-1])

        t1 = before_pose['timestamp']
        t2 = after_pose['timestamp']
        ratio = (frame_timestamp - t1) / (t2 - t1) if t2 != t1 else 0.0

        result = {'timestamp': frame_timestamp}
        all_keys = set(before_pose.keys()) | set(after_pose.keys())
        angle_keys = {'yaw', 'pitch', 'roll', 'gimbal_pitch', 'gimbal_yaw', 'gimbal_roll'}

        for key in all_keys:
            if key == 'timestamp':
                continue
            is_angle = key in angle_keys
            val = self._interpolate_field(before_pose, after_pose, key, ratio, is_angle=is_angle)
            if val is not None:
                result[key] = val

        return result
    
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
