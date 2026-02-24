"""
SRT字幕解析器
解析DJI SRT字幕文件，提取GPS、高度、姿态等数据
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger


class SRTParser:
    """SRT字幕解析器类"""
    
    def __init__(self):
        """初始化SRT解析器"""
        self.pose_data = []
    
    def parse(self, srt_path: str) -> List[Dict[str, Any]]:
        """
        解析SRT文件
        
        Args:
            srt_path: SRT文件路径
            
        Returns:
            位姿数据列表
        """
        try:
            with open(srt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 分割字幕块
            subtitle_blocks = content.strip().split('\n\n')
            
            self.pose_data = []
            
            for block in subtitle_blocks:
                pose = self._parse_block(block)
                if pose:
                    self.pose_data.append(pose)
            
            logger.info(f"成功解析SRT文件: {srt_path}, 共{len(self.pose_data)}条位姿数据")
            
            return self.pose_data
            
        except Exception as e:
            logger.error(f"解析SRT文件时发生错误: {e}")
            return []
    
    def _parse_block(self, block: str) -> Optional[Dict[str, Any]]:
        """
        解析单个字幕块
        
        Args:
            block: 字幕块文本
            
        Returns:
            位姿数据字典
        """
        try:
            lines = block.strip().split('\n')
            
            if len(lines) < 3:
                return None
            
            # 第一行: 序号
            block_number = int(lines[0])
            
            # 第二行: 时间戳
            timestamp_line = lines[1]
            timestamp = self._parse_timestamp(timestamp_line)
            
            # 第三行及之后: 字幕内容
            content = '\n'.join(lines[2:])
            
            # 解析位姿数据
            pose = {
                'block_number': block_number,
                'timestamp': timestamp,
            }
            
            # 解析帧号
            frame_match = re.search(r'FrameCnt:\s*(\d+)', content)
            if frame_match:
                pose['frame_number'] = int(frame_match.group(1))
            
            # 解析时间差
            diff_time_match = re.search(r'DiffTime:\s*(\d+)ms', content)
            if diff_time_match:
                pose['diff_time'] = int(diff_time_match.group(1))
            
            # 解析日期时间
            datetime_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)', content)
            if datetime_match:
                pose['datetime'] = datetime_match.group(1)
            
            # 解析GPS坐标
            lat_match = re.search(r'latitude:\s*([-+]?\d+\.\d+)', content, re.IGNORECASE)
            lon_match = re.search(r'longitude:\s*([-+]?\d+\.\d+)', content, re.IGNORECASE)
            
            if lat_match and lon_match:
                pose['latitude'] = float(lat_match.group(1))
                pose['longitude'] = float(lon_match.group(1))
            
            # 解析高度
            alt_match = re.search(r'altitude:\s*([-+]?\d+\.?\d*)m?', content, re.IGNORECASE)
            if alt_match:
                pose['altitude'] = float(alt_match.group(1))
            
            # 解析姿态角
            yaw_match = re.search(r'yaw:\s*([-+]?\d+\.?\d*)', content, re.IGNORECASE)
            pitch_match = re.search(r'pitch:\s*([-+]?\d+\.?\d*)', content, re.IGNORECASE)
            roll_match = re.search(r'roll:\s*([-+]?\d+\.?\d*)', content, re.IGNORECASE)
            
            if yaw_match:
                pose['yaw'] = float(yaw_match.group(1))
            if pitch_match:
                pose['pitch'] = float(pitch_match.group(1))
            if roll_match:
                pose['roll'] = float(roll_match.group(1))
            
            # 检查是否至少有GPS坐标
            if 'latitude' not in pose or 'longitude' not in pose:
                logger.warning(f"字幕块 {block_number} 缺少GPS坐标")
                return None
            
            return pose
            
        except Exception as e:
            logger.debug(f"解析字幕块失败: {e}")
            return None
    
    def _parse_timestamp(self, timestamp_line: str) -> float:
        """
        解析SRT时间戳
        
        Args:
            timestamp_line: 时间戳行，格式如 "00:00:00,000 --> 00:00:00,033"
            
        Returns:
            时间戳 (毫秒)
        """
        try:
            # 提取起始时间
            start_time = timestamp_line.split('-->')[0].strip()
            
            # 解析时间格式 HH:MM:SS,mmm
            time_parts = start_time.replace(',', ':').split(':')
            
            hours = int(time_parts[0])
            minutes = int(time_parts[1])
            seconds = int(time_parts[2])
            milliseconds = int(time_parts[3])
            
            # 转换为毫秒
            total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
            
            return total_ms
            
        except Exception as e:
            logger.warning(f"解析时间戳失败: {timestamp_line}, 错误: {e}")
            return 0.0
    
    def get_pose_by_timestamp(self, timestamp: float, tolerance: float = 100.0) -> Optional[Dict[str, Any]]:
        """
        根据时间戳获取位姿数据
        
        Args:
            timestamp: 目标时间戳 (毫秒)
            tolerance: 容差 (毫秒)
            
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
    
    def get_pose_by_frame_number(self, frame_number: int) -> Optional[Dict[str, Any]]:
        """
        根据帧号获取位姿数据
        
        Args:
            frame_number: 帧号
            
        Returns:
            对应的位姿数据
        """
        for pose in self.pose_data:
            if pose.get('frame_number') == frame_number:
                return pose
        
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
        logger.info(f"=== SRT位姿数据示例 (前{count}条) ===")
        
        for i, pose in enumerate(self.pose_data[:count]):
            logger.info(f"[{i+1}] 帧号: {pose.get('frame_number', 'N/A')}, "
                       f"时间戳: {pose.get('timestamp', 0):.2f}ms, "
                       f"GPS: ({pose.get('latitude', 0):.6f}, {pose.get('longitude', 0):.6f}), "
                       f"高度: {pose.get('altitude', 0):.1f}m")
