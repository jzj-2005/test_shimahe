"""
后处理器模块
在pipeline结束后自动执行的后处理任务

任务包括：
1. 智能去重
2. 导出GeoJSON（原始、去重、高置信度）
3. 生成HTML可视化地图
4. 生成统计摘要
"""

import os
import math
from pathlib import Path
from typing import Dict, Any
import pandas as pd
from loguru import logger

from .deduplication import DetectionDeduplicator
from .geojson_writer import GeoJSONWriter
from .map_generator import MapGenerator


class PostProcessor:
    """后处理器类"""
    
    def __init__(self, output_config: Dict[str, Any]):
        """
        初始化后处理器
        
        Args:
            output_config: 输出配置字典（来自realtime_config.yaml或offline_config.yaml）
        """
        self.config = output_config
        
        # 功能开关
        self.enable_geojson = output_config.get('export_geojson', True)
        self.enable_dedup = output_config.get('enable_deduplication', True)
        self.enable_map = output_config.get('generate_map', True)
        self.enable_summary = output_config.get('generate_summary', True)
        self.auto_open_map = output_config.get('auto_open_map', False)
        
        # 初始化子模块
        self.deduplicator = None
        self.geojson_writer = None
        self.map_generator = None
        
        if self.enable_dedup:
            dedup_config = output_config.get('deduplication', {})
            self.deduplicator = DetectionDeduplicator(dedup_config)
        
        if self.enable_geojson:
            self.geojson_writer = GeoJSONWriter(output_config)
        
        if self.enable_map:
            self.map_generator = MapGenerator(output_config)
        
        logger.info("后处理器初始化完成")
        logger.info(f"  - GeoJSON导出: {'开启' if self.enable_geojson else '关闭'}")
        logger.info(f"  - 智能去重: {'开启' if self.enable_dedup else '关闭'}")
        logger.info(f"  - 地图生成: {'开启' if self.enable_map else '关闭'}")
    
    def process(self, csv_path: str, output_base_dir: str = None) -> Dict[str, Any]:
        """
        执行所有后处理任务
        
        Args:
            csv_path: CSV文件路径
            output_base_dir: 输出基础目录（可选）
            
        Returns:
            处理结果字典
        """
        results = {
            'success': False,
            'csv_path': csv_path,
            'files': {}
        }
        
        try:
            # 检查CSV文件是否存在
            if not os.path.exists(csv_path):
                logger.error(f"CSV文件不存在: {csv_path}")
                return results
            
            # 确定输出目录
            if output_base_dir is None:
                output_base_dir = os.path.dirname(os.path.dirname(csv_path))
            
            logger.info("="*60)
            logger.info("开始后处理...")
            logger.info("="*60)
            
            # 读取CSV数据
            df_raw = pd.read_csv(csv_path)
            logger.info(f"读取检测数据: {len(df_raw)} 条记录")
            
            if len(df_raw) == 0:
                logger.warning("检测数据为空，跳过后处理")
                results['success'] = True
                return results
            
            results['original_count'] = len(df_raw)
            
            # 任务1：智能去重
            df_unique = df_raw
            if self.enable_dedup and self.deduplicator:
                logger.info("执行智能去重...")
                df_unique = self.deduplicator.deduplicate_dataframe(df_raw)
                
                results['deduplication'] = {
                    'original': len(df_raw),
                    'unique': len(df_unique),
                    'removed': len(df_raw) - len(df_unique),
                    'removal_rate': (len(df_raw) - len(df_unique)) / len(df_raw) * 100 if len(df_raw) > 0 else 0
                }
            else:
                logger.info("去重功能未启用，使用原始数据")
            
            results['unique_count'] = len(df_unique)
            
            # 任务2：导出GeoJSON
            if self.enable_geojson and self.geojson_writer:
                logger.info("导出GeoJSON文件...")
                geojson_dir = os.path.join(output_base_dir, 'geojson')
                
                geojson_files = self.geojson_writer.export_multiple(
                    df_raw=df_raw,
                    df_unique=df_unique,
                    output_dir=geojson_dir
                )
                
                results['files']['geojson'] = geojson_files
            
            # 任务3：生成HTML地图（使用去重后的数据）
            if self.enable_map and self.map_generator and geojson_files:
                logger.info("生成HTML地图...")
                map_path = self.config.get('map_output_path', 
                                          os.path.join(output_base_dir, 'map.html'))
                
                # 确保目录存在
                os.makedirs(os.path.dirname(map_path), exist_ok=True)
                
                # 使用去重后的GeoJSON生成地图
                map_file = self.map_generator.generate(
                    geojson_files['unique'], 
                    map_path
                )
                
                if map_file:
                    results['files']['map'] = map_file
                    
                    # 可选：自动打开浏览器
                    if self.auto_open_map:
                        try:
                            import webbrowser
                            abs_path = os.path.abspath(map_file)
                            webbrowser.open(f'file:///{abs_path}')
                            logger.info("✓ 地图已在浏览器中打开")
                        except Exception as e:
                            logger.warning(f"自动打开浏览器失败: {e}")
            
            # 任务4：生成统计摘要
            if self.enable_summary:
                logger.info("生成统计摘要...")
                summary_path = self.config.get('summary_path',
                                              os.path.join(output_base_dir, 'summary.txt'))
                
                summary_file = self._generate_summary(df_raw, df_unique, summary_path)
                if summary_file:
                    results['files']['summary'] = summary_file
            
            results['success'] = True
            
            logger.info("="*60)
            logger.info("✓ 后处理完成")
            logger.info("="*60)
            
            # 输出文件清单
            if results['files']:
                logger.info("生成的文件:")
                for file_type, file_path in results['files'].items():
                    if isinstance(file_path, dict):
                        for sub_type, sub_path in file_path.items():
                            logger.info(f"  - {file_type}.{sub_type}: {sub_path}")
                    else:
                        logger.info(f"  - {file_type}: {file_path}")
            
            return results
            
        except Exception as e:
            logger.error(f"后处理过程中发生错误: {e}", exc_info=True)
            results['error'] = str(e)
            return results
    
    def _generate_summary(
        self, 
        df_raw: pd.DataFrame, 
        df_unique: pd.DataFrame,
        output_path: str
    ) -> str:
        """
        生成统计摘要文件
        
        Args:
            df_raw: 原始数据
            df_unique: 去重后数据
            output_path: 输出路径
            
        Returns:
            生成的文件路径
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("="*70 + "\n")
                f.write("石马河四乱检测系统 - 检测结果统计摘要\n")
                f.write("="*70 + "\n\n")
                
                # 基本统计
                f.write("## 1. 数据概览\n")
                f.write("-"*70 + "\n")
                f.write(f"原始检测总数: {len(df_raw)} 条\n")
                
                if self.enable_dedup and len(df_unique) != len(df_raw):
                    removed = len(df_raw) - len(df_unique)
                    rate = removed / len(df_raw) * 100 if len(df_raw) > 0 else 0
                    f.write(f"去重后数量: {len(df_unique)} 条\n")
                    f.write(f"去除重复: {removed} 条 ({rate:.1f}%)\n")
                
                # 使用去重后的数据进行统计
                df = df_unique if len(df_unique) > 0 else df_raw
                
                # 按类别统计
                f.write("\n## 2. 按类别统计\n")
                f.write("-"*70 + "\n")
                class_counts = df['class_name'].value_counts()
                for class_name, count in class_counts.items():
                    percentage = count / len(df) * 100
                    f.write(f"  {class_name:20s}: {count:5d} ({percentage:5.1f}%)\n")
                
                # 置信度统计
                f.write("\n## 3. 置信度统计\n")
                f.write("-"*70 + "\n")
                f.write(f"  平均置信度: {df['confidence'].mean():.3f}\n")
                f.write(f"  最高置信度: {df['confidence'].max():.3f}\n")
                f.write(f"  最低置信度: {df['confidence'].min():.3f}\n")
                f.write(f"  中位数置信度: {df['confidence'].median():.3f}\n")
                
                # 地理坐标范围
                f.write("\n## 4. 地理坐标范围\n")
                f.write("-"*70 + "\n")
                f.write(f"  纬度范围: {df['center_lat'].min():.6f} ~ {df['center_lat'].max():.6f}\n")
                f.write(f"  经度范围: {df['center_lon'].min():.6f} ~ {df['center_lon'].max():.6f}\n")
                f.write(f"  高度范围: {df['altitude'].min():.1f}m ~ {df['altitude'].max():.1f}m\n")
                
                # 计算覆盖范围
                lat_range = (df['center_lat'].max() - df['center_lat'].min()) * 110540
                lon_avg_lat = df['center_lat'].mean()
                lon_range = (df['center_lon'].max() - df['center_lon'].min()) * 111320 * math.cos(math.radians(lon_avg_lat))
                f.write(f"  覆盖范围: 约 {lat_range:.0f}m × {lon_range:.0f}m\n")
                
                # GPS质量统计（如果有）
                if 'gps_quality' in df.columns and df['gps_quality'].notna().any():
                    f.write("\n## 5. GPS质量统计\n")
                    f.write("-"*70 + "\n")
                    quality_counts = df['gps_quality'].value_counts()
                    for quality, count in quality_counts.items():
                        percentage = count / len(df) * 100
                        f.write(f"  {quality:15s}: {count:5d} ({percentage:5.1f}%)\n")
                    
                    if 'estimated_error' in df.columns:
                        f.write(f"\n  平均定位误差: {df['estimated_error'].mean():.2f}m\n")
                        f.write(f"  最大定位误差: {df['estimated_error'].max():.2f}m\n")
                
                # 边缘检测统计
                if 'is_on_edge' in df.columns:
                    edge_count = df['is_on_edge'].sum()
                    f.write("\n## 6. 边缘检测统计\n")
                    f.write("-"*70 + "\n")
                    f.write(f"  边缘检测数: {edge_count} ({edge_count/len(df)*100:.1f}%)\n")
                    f.write(f"  完整检测数: {len(df) - edge_count} ({(len(df)-edge_count)/len(df)*100:.1f}%)\n")
                
                f.write("\n" + "="*70 + "\n")
                f.write("统计摘要生成完成\n")
                f.write("="*70 + "\n")
            
            logger.info(f"✓ 生成统计摘要: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"生成统计摘要失败: {e}")
            return ""
    
    def is_enabled(self) -> bool:
        """
        检查后处理器是否启用
        
        Returns:
            是否启用任何后处理功能
        """
        return (self.enable_geojson or 
                self.enable_map or 
                self.enable_summary)
