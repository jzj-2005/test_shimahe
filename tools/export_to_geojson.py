# -*- coding: utf-8 -*-
"""
GeoJSON导出工具 - Windows兼容版本
将CSV检测结果转换为GeoJSON格式用于地图可视化
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pandas as pd
except ImportError:
    print("[ERROR] 需要安装pandas库")
    print("请运行: pip install pandas")
    sys.exit(1)


def read_csv_detections(csv_path: str) -> pd.DataFrame:
    """读取CSV检测结果"""
    try:
        df = pd.read_csv(csv_path)
        print("[OK] 读取CSV文件: {}".format(csv_path))
        print("  总记录数: {}".format(len(df)))
        return df
    except Exception as e:
        print("[ERROR] 读取CSV文件失败: {}".format(e))
        sys.exit(1)


def detection_to_geojson_feature(row: pd.Series) -> Dict[str, Any]:
    """将单条检测记录转换为GeoJSON Feature"""
    # 提取四角点坐标构成多边形
    coordinates = [[
        [row['corner1_lon'], row['corner1_lat']],
        [row['corner2_lon'], row['corner2_lat']],
        [row['corner3_lon'], row['corner3_lat']],
        [row['corner4_lon'], row['corner4_lat']],
        [row['corner1_lon'], row['corner1_lat']]  # 闭合多边形
    ]]
    
    # 构建Feature
    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": coordinates
        },
        "properties": {
            "frame_number": int(row['frame_number']),
            "class_id": int(row['class_id']),
            "class_name": str(row['class_name']),
            "confidence": float(row['confidence']),
            "center_lat": float(row['center_lat']),
            "center_lon": float(row['center_lon']),
            "altitude": float(row['altitude']),
            "drone_lat": float(row['drone_lat']),
            "drone_lon": float(row['drone_lon']),
            "is_on_edge": bool(row.get('is_on_edge', False)),
            "edge_positions": str(row.get('edge_positions', '')),
            "image_path": str(row.get('image_path', ''))
        }
    }
    
    return feature


def export_to_geojson(
    df: pd.DataFrame,
    output_path: str,
    min_confidence: float = 0.0,
    class_filter: List[str] = None
) -> int:
    """
    导出为GeoJSON格式
    
    坐标系说明：
    - 输出坐标系：CGCS2000 (EPSG:4490)
    - 来源：DJI无人机GPS原始坐标为WGS84，已自动转换为CGCS2000
    """
    # 过滤
    filtered_df = df.copy()
    
    if min_confidence > 0:
        filtered_df = filtered_df[filtered_df['confidence'] >= min_confidence]
        print("  置信度过滤 (>={0}): 保留 {1} 条".format(min_confidence, len(filtered_df)))
    
    if class_filter:
        filtered_df = filtered_df[filtered_df['class_name'].isin(class_filter)]
        print("  类别过滤: 保留 {} 条".format(len(filtered_df)))
    
    # 转换为GeoJSON Features
    features = []
    for _, row in filtered_df.iterrows():
        try:
            feature = detection_to_geojson_feature(row)
            features.append(feature)
        except Exception as e:
            print("  [WARN] 跳过无效记录 (frame {}): {}".format(row['frame_number'], e))
    
    # 构建FeatureCollection
    geojson = {
        "type": "FeatureCollection",
        "crs": {  # 坐标参考系统声明
            "type": "name",
            "properties": {
                "name": "urn:ogc:def:crs:EPSG::4490"  # CGCS2000坐标系
            }
        },
        "features": features,
        "properties": {
            "total_detections": len(features),
            "source": "Drone Water Inspection System",
            "coordinate_system": "CGCS2000",
            "coordinate_note": "Converted from WGS84 (drone GPS) to CGCS2000 (national standard)",
            "epsg_code": "EPSG:4490",
            "min_confidence": min_confidence
        }
    }
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
    
    print("[OK] 导出GeoJSON: {}".format(output_path))
    print("  导出记录数: {}".format(len(features)))
    
    return len(features)


def generate_summary(df: pd.DataFrame, output_dir: str):
    """生成统计摘要"""
    summary_path = Path(output_dir) / "summary.txt"
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("="*60 + "\n")
        f.write("检测结果统计摘要\n")
        f.write("="*60 + "\n\n")
        
        f.write("总检测数: {}\n\n".format(len(df)))
        
        f.write("按类别统计:\n")
        f.write("-"*60 + "\n")
        class_counts = df['class_name'].value_counts()
        for class_name, count in class_counts.items():
            percentage = count / len(df) * 100
            f.write("  {0:20s}: {1:5d} ({2:5.1f}%)\n".format(class_name, count, percentage))
        
        f.write("\n置信度统计:\n")
        f.write("-"*60 + "\n")
        f.write("  平均置信度: {:.3f}\n".format(df['confidence'].mean()))
        f.write("  最大置信度: {:.3f}\n".format(df['confidence'].max()))
        f.write("  最小置信度: {:.3f}\n".format(df['confidence'].min()))
        
        f.write("\n地理坐标范围:\n")
        f.write("-"*60 + "\n")
        f.write("  纬度: {:.6f} - {:.6f}\n".format(df['center_lat'].min(), df['center_lat'].max()))
        f.write("  经度: {:.6f} - {:.6f}\n".format(df['center_lon'].min(), df['center_lon'].max()))
        
        # 计算覆盖范围
        lat_range = (df['center_lat'].max() - df['center_lat'].min()) * 110540
        lon_avg_lat = df['center_lat'].mean()
        import math
        lon_range = (df['center_lon'].max() - df['center_lon'].min()) * 111320 * math.cos(math.radians(lon_avg_lat))
        f.write("  覆盖范围: 约 {:.0f}米 x {:.0f}米\n".format(lat_range, lon_range))
        
        if 'is_on_edge' in df.columns:
            edge_count = df['is_on_edge'].sum()
            f.write("\n边缘检测数: {} ({:.1f}%)\n".format(edge_count, edge_count/len(df)*100))
        
        f.write("\n" + "="*60 + "\n")
    
    print("[OK] 生成统计摘要: {}".format(summary_path))


def main():
    parser = argparse.ArgumentParser(description='导出检测结果为GeoJSON格式')
    parser.add_argument('csv_file', help='CSV检测结果文件路径')
    parser.add_argument('--output-dir', '-o', default='./data/output/offline',
                       help='输出目录 (默认: ./data/output)')
    parser.add_argument('--min-confidence', '-c', type=float, default=0.0,
                       help='最小置信度阈值 (默认: 0.0)')
    parser.add_argument('--high-conf-threshold', type=float, default=0.5,
                       help='高置信度阈值 (默认: 0.5)')
    parser.add_argument('--classes', nargs='+', 
                       help='只导出指定类别')
    
    args = parser.parse_args()
    
    # 读取CSV
    df = read_csv_detections(args.csv_file)
    
    # 创建输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*60)
    print("开始导出GeoJSON")
    print("="*60)
    
    # 导出所有检测
    all_output = output_dir / "detections.geojson"
    count_all = export_to_geojson(df, str(all_output), args.min_confidence, args.classes)
    
    # 导出高置信度检测
    high_conf_output = output_dir / "detections_high_conf.geojson"
    count_high = export_to_geojson(df, str(high_conf_output), args.high_conf_threshold, args.classes)
    
    # 生成统计摘要
    print("\n生成统计摘要...")
    generate_summary(df, str(output_dir))
    
    print("\n" + "="*60)
    print("导出完成！")
    print("="*60)
    print("  所有检测:     {}".format(all_output))
    print("  高置信度检测: {} (>={})".format(high_conf_output, args.high_conf_threshold))
    print("  统计摘要:     {}".format(output_dir / 'summary.txt'))
    print("\n下一步: 使用 quick_visualize.py 在地图上查看结果")


if __name__ == '__main__':
    main()
