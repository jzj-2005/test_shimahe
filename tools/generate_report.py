# -*- coding: utf-8 -*-
"""
报告生成工具 - Windows兼容版本
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
import sys

try:
    import pandas as pd
except ImportError:
    print("[ERROR] 需要安装pandas库")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='生成检测结果报告')
    parser.add_argument('csv_file', nargs='?', default='./data/output/csv/detections_offline.csv')
    parser.add_argument('--output', '-o', default='./data/output/delivery_report.md')
    args = parser.parse_args()
    
    if not Path(args.csv_file).exists():
        print("[ERROR] 文件不存在: {}".format(args.csv_file))
        sys.exit(1)
    
    print("="*60)
    print("生成检测报告")
    print("="*60)
    
    df = pd.read_csv(args.csv_file)
    print("  总记录数: {}".format(len(df)))
    
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write("# 无人机水利四乱检测系统 - 检测报告\n\n")
        f.write("**生成时间**: {}\n\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        f.write("## 1. 处理概况\n\n")
        f.write("- **总检测数**: {} 个目标\n".format(len(df)))
        f.write("- **平均置信度**: {:.3f}\n\n".format(df['confidence'].mean()))
        
        f.write("## 2. 检测统计\n\n")
        f.write("### 按类别统计\n\n| 类别 | 数量 | 占比 |\n|-----|------|------|\n")
        class_counts = df['class_name'].value_counts()
        for class_name, count in class_counts.items():
            percentage = count / len(df) * 100
            f.write("| {} | {} | {:.1f}% |\n".format(class_name, count, percentage))
        
        f.write("\n## 3. 地理坐标信息\n\n")
        f.write("- **纬度范围**: {:.6f} - {:.6f}\n".format(df['center_lat'].min(), df['center_lat'].max()))
        f.write("- **经度范围**: {:.6f} - {:.6f}\n".format(df['center_lon'].min(), df['center_lon'].max()))
        
        f.write("\n## 4. 交付物清单\n\n")
        f.write("- [x] CSV检测结果\n")
        f.write("- [x] GeoJSON可视化文件\n")
        f.write("- [x] 交互式地图\n")
        f.write("- [x] 处理报告\n\n")
        f.write("**报告生成时间**: {}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    
    print("[OK] 生成报告: {}".format(args.output))
    print("\n提示: 可用Markdown阅读器查看")


if __name__ == '__main__':
    main()
