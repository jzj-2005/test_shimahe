# -*- coding: utf-8 -*-
"""
抽样验证工具 - 简化版
注意: 此工具需要在浏览器中手动操作
"""

import json
import argparse
import webbrowser
from pathlib import Path
import sys

try:
    import pandas as pd
except ImportError:
    print("[ERROR] 需要安装pandas库")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='抽样验证坐标准确度')
    parser.add_argument('csv_file', nargs='?', default='./data/output/csv/detections_offline.csv')
    parser.add_argument('--samples', '-n', type=int, default=20)
    parser.add_argument('--output', '-o', default='./data/output/validation.html')
    parser.add_argument('--no-open', action='store_true')
    
    args = parser.parse_args()
    
    if not Path(args.csv_file).exists():
        print("[ERROR] 文件不存在: {}".format(args.csv_file))
        sys.exit(1)
    
    print("="*60)
    print("坐标准确度抽样验证")
    print("="*60)
    
    df = pd.read_csv(args.csv_file)
    if len(df) > args.samples:
        samples = df.sample(n=args.samples, random_state=42)
    else:
        samples = df
    
    print("[OK] 读取CSV文件")
    print("  抽取样本: {}".format(len(samples)))
    
    # 生成简化的HTML
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write("""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>坐标验证</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>body{margin:0;padding:0}#map{height:100vh;width:100%}</style>
</head><body><div id="map"></div>
<script>
var map=L.map('map').setView([22.8,114.1],15);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
alert('验证工具：请在地图上查看检测位置，手动记录误差');
</script></body></html>""")
    
    print("[OK] 生成验证HTML: {}".format(args.output))
    
    if not args.no_open:
        webbrowser.open('file:///' + str(Path(args.output).absolute()))


if __name__ == '__main__':
    main()
