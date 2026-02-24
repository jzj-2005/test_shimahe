"""
SRT字幕提取器
从DJI视频文件中提取嵌入的SRT字幕轨道
"""

import os
import subprocess
from typing import Optional
from loguru import logger


class SRTExtractor:
    """SRT字幕提取器类"""
    
    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        temp_dir: str = "./data/temp/srt",
        subtitle_stream_index: int = 0
    ):
        """
        初始化SRT提取器
        
        Args:
            ffmpeg_path: FFmpeg可执行文件路径
            temp_dir: 临时文件存储目录
            subtitle_stream_index: 字幕轨道索引
        """
        self.ffmpeg_path = ffmpeg_path
        self.temp_dir = temp_dir
        self.subtitle_stream_index = subtitle_stream_index
        
        # 创建临时目录
        os.makedirs(temp_dir, exist_ok=True)
    
    def extract(
        self,
        video_path: str,
        output_srt_path: Optional[str] = None,
        force: bool = False
    ) -> Optional[str]:
        """
        从视频文件中提取SRT字幕
        
        Args:
            video_path: 视频文件路径
            output_srt_path: 输出SRT文件路径 (如果为None，自动生成)
            force: 是否强制重新提取 (即使SRT文件已存在)
            
        Returns:
            提取的SRT文件路径，失败返回None
        """
        # 检查视频文件是否存在
        if not os.path.exists(video_path):
            logger.error(f"视频文件不存在: {video_path}")
            return None
        
        # 自动生成输出路径
        if output_srt_path is None:
            video_basename = os.path.basename(video_path)
            video_name = os.path.splitext(video_basename)[0]
            output_srt_path = os.path.join(self.temp_dir, f"{video_name}.srt")
        
        # 如果SRT文件已存在且不强制重新提取，直接返回
        if os.path.exists(output_srt_path) and not force:
            logger.info(f"SRT文件已存在，跳过提取: {output_srt_path}")
            return output_srt_path
        
        # 检查FFmpeg是否可用
        if not self._check_ffmpeg():
            logger.error("FFmpeg不可用，请确保FFmpeg已安装并在PATH中")
            return None
        
        # 检查视频是否包含字幕轨道
        if not self._has_subtitle_stream(video_path):
            logger.warning(f"视频文件不包含字幕轨道: {video_path}")
            return None
        
        # 提取字幕
        try:
            logger.info(f"正在提取SRT字幕: {video_path} -> {output_srt_path}")
            
            cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-map', f'0:s:{self.subtitle_stream_index}',
                '-c:s', 'srt',
                '-y',  # 覆盖输出文件
                output_srt_path
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                logger.info(f"SRT字幕提取成功: {output_srt_path}")
                return output_srt_path
            else:
                logger.error(f"SRT字幕提取失败: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"提取SRT字幕时发生错误: {e}")
            return None
    
    def _check_ffmpeg(self) -> bool:
        """
        检查FFmpeg是否可用
        
        Returns:
            是否可用
        """
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"检查FFmpeg时发生异常: {e}")
            return False
    
    def _has_subtitle_stream(self, video_path: str) -> bool:
        """
        检查视频是否包含字幕轨道
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            是否包含字幕轨道
        """
        try:
            cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-hide_banner'
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            # FFmpeg的流信息在stderr中
            output = result.stderr
            
            # 查找字幕流
            return 'Stream' in output and 'Subtitle' in output
            
        except Exception as e:
            logger.error(f"检查字幕轨道时发生错误: {e}")
            return False
    
    def auto_find_srt(self, video_path: str) -> Optional[str]:
        """
        自动查找与视频同名的SRT文件
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            SRT文件路径，未找到返回None
        """
        video_dir = os.path.dirname(video_path)
        video_basename = os.path.basename(video_path)
        video_name = os.path.splitext(video_basename)[0]
        
        # 尝试在视频同目录查找
        srt_path = os.path.join(video_dir, f"{video_name}.srt")
        if os.path.exists(srt_path):
            logger.info(f"找到同名SRT文件: {srt_path}")
            return srt_path
        
        # 尝试在临时目录查找
        srt_path = os.path.join(self.temp_dir, f"{video_name}.srt")
        if os.path.exists(srt_path):
            logger.info(f"找到已提取的SRT文件: {srt_path}")
            return srt_path
        
        logger.info("未找到同名SRT文件")
        return None
    
    def get_or_extract(self, video_path: str) -> Optional[str]:
        """
        获取或提取SRT文件
        先查找同名SRT文件，如果没有则从视频中提取
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            SRT文件路径
        """
        # 先尝试自动查找
        srt_path = self.auto_find_srt(video_path)
        if srt_path:
            return srt_path
        
        # 如果没找到，尝试提取
        logger.info("未找到现有SRT文件，尝试从视频中提取")
        return self.extract(video_path)
