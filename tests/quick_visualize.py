# -*- coding: utf-8 -*-
"""
快速可视化工具 - Windows兼容版本
在浏览器中打开交互式地图显示检测结果
"""

import json
import argparse
import webbrowser
from pathlib import Path
import sys


def load_geojson(geojson_path: str) -> dict:
    """加载GeoJSON文件"""
    try:
        with open(geojson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print("[OK] 加载GeoJSON文件: {}".format(geojson_path))
        print("  检测数量: {}".format(len(data.get('features', []))))
        return data
    except Exception as e:
        print("[ERROR] 加载GeoJSON失败: {}".format(e))
        sys.exit(1)


def calculate_bounds(geojson: dict) -> tuple:
    """计算GeoJSON数据的边界"""
    features = geojson.get('features', [])
    if not features:
        return (22.5, 114.0, 23.5, 115.0)
    
    lats = []
    lons = []
    
    for feature in features:
        props = feature.get('properties', {})
        if 'center_lat' in props and 'center_lon' in props:
            lats.append(props['center_lat'])
            lons.append(props['center_lon'])
    
    if lats and lons:
        return (min(lats), min(lons), max(lats), max(lons))
    else:
        return (22.5, 114.0, 23.5, 115.0)


def generate_html(geojson: dict, output_path: str):
    """生成HTML地图文件"""
    min_lat, min_lon, max_lat, max_lon = calculate_bounds(geojson)
    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2
    
    geojson_str = json.dumps(geojson, ensure_ascii=False)
    
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>无人机检测结果可视化</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body { margin: 0; padding: 0; font-family: Arial, sans-serif; }
        #map { height: 100vh; width: 100%; }
        .info-panel {
            position: absolute; top: 10px; right: 10px;
            background: white; padding: 15px; border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2); z-index: 1000; max-width: 300px;
        }
        .info-panel h3 { margin-top: 0; font-size: 16px; }
        .legend {
            position: absolute; bottom: 30px; right: 10px;
            background: white; padding: 10px; border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2); z-index: 1000;
        }
        .legend-item { display: flex; align-items: center; margin: 5px 0; font-size: 12px; }
        .legend-color { width: 20px; height: 20px; margin-right: 8px; border: 1px solid #333; }
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="info-panel">
        <h3>无人机检测结果</h3>
        <p>总检测数: <strong id="total-count">0</strong></p>
        <p>点击检测框查看详情</p>
    </div>
    <div class="legend"><strong>图例</strong><div id="legend-items"></div></div>
    <script>
        var map = L.map('map').setView([CENTER_LAT, CENTER_LON], 15);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap', maxZoom: 19
        }).addTo(map);
        
        var geojsonData = GEOJSON_DATA;
        var classColors = {
            'Water Bodies': '#007bff', 'Vegetation': '#28a745', 'Mining Area': '#6f42c1',
            'Debris': '#fd7e14', 'Industrial Buildings': '#6c757d', 'Waterway Facilities': '#17a2b8',
            'Hydraulic Controls': '#e83e8c', 'Residences': '#ffc107', 'Sheds': '#20c997',
            'Storage Zones': '#dc3545', 'Recreation Areas': '#f8f9fa'
        };
        
        function style(feature) {
            var color = classColors[feature.properties.class_name] || '#6c757d';
            var opacity = 0.4 + feature.properties.confidence * 0.4;
            return { fillColor: color, weight: 2, opacity: 1, color: color, fillOpacity: opacity };
        }
        
        function onEachFeature(feature, layer) {
            if (feature.properties) {
                var p = feature.properties;
                layer.bindPopup('<strong>' + p.class_name + '</strong><br>' +
                    '置信度: ' + (p.confidence * 100).toFixed(1) + '%<br>' +
                    '帧号: ' + p.frame_number + '<br>' +
                    '坐标: ' + p.center_lat.toFixed(6) + ', ' + p.center_lon.toFixed(6));
            }
        }
        
        var geojsonLayer = L.geoJSON(geojsonData, { style: style, onEachFeature: onEachFeature }).addTo(map);
        map.fitBounds(geojsonLayer.getBounds(), {padding: [50, 50]});
        
        document.getElementById('total-count').textContent = geojsonData.features.length;
        
        var classSet = new Set();
        geojsonData.features.forEach(function(f) { classSet.add(f.properties.class_name); });
        var legendItems = document.getElementById('legend-items');
        Array.from(classSet).sort().forEach(function(cn) {
            var color = classColors[cn] || '#6c757d';
            var item = document.createElement('div');
            item.className = 'legend-item';
            item.innerHTML = '<div class="legend-color" style="background-color: ' + color + '"></div><span>' + cn + '</span>';
            legendItems.appendChild(item);
        });
    </script>
</body>
</html>""".replace("CENTER_LAT", str(center_lat)).replace("CENTER_LON", str(center_lon)).replace("GEOJSON_DATA", geojson_str)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("[OK] 生成HTML地图: {}".format(output_path))


def main():
    parser = argparse.ArgumentParser(description='在浏览器中可视化GeoJSON检测结果')
    parser.add_argument('geojson_file', nargs='?', default='./data/output/offline/detections.geojson')
    parser.add_argument('--output', '-o', default='./data/output/offline/map.html')
    parser.add_argument('--no-open', action='store_true')
    
    args = parser.parse_args()
    
    if not Path(args.geojson_file).exists():
        print("[ERROR] 文件不存在: {}".format(args.geojson_file))
        print("请先运行 export_to_geojson.py 生成GeoJSON文件")
        sys.exit(1)
    
    print("="*60)
    print("生成交互式地图")
    print("="*60)
    
    geojson = load_geojson(args.geojson_file)
    generate_html(geojson, args.output)
    
    print("\n" + "="*60)
    print("地图生成完成！")
    print("="*60)
    print("  HTML文件: {}".format(args.output))
    
    if not args.no_open:
        print("\n正在打开浏览器...")
        output_path = Path(args.output).absolute()
        webbrowser.open('file:///' + str(output_path))
        print("[OK] 浏览器已打开")


if __name__ == '__main__':
    main()
