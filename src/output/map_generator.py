"""
地图生成模块
生成交互式HTML地图用于可视化检测结果

使用：Leaflet.js
特性：
1. 检测框多边形显示
2. 类别颜色图例
3. 点击弹窗显示详情
4. 自适应地图边界
5. GPS质量信息展示
"""

import json
import os
from typing import Dict, Any
from loguru import logger


class MapGenerator:
    """地图生成器类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化地图生成器
        
        Args:
            config: 配置字典
        """
        if config is None:
            config = {}
        
        self.config = config
        
        # 地图样式配置
        self.class_colors = {
            '违建': '#dc3545',      # 红色
            '垃圾': '#fd7e14',      # 橙色
            '污水': '#6f42c1',      # 紫色
            '违种': '#28a745',      # 绿色
            'Water Bodies': '#007bff',
            'Vegetation': '#28a745',
            'Mining Area': '#6f42c1',
            'Debris': '#fd7e14',
            'Industrial Buildings': '#6c757d',
            'Waterway Facilities': '#17a2b8',
            'Hydraulic Controls': '#e83e8c',
            'Residences': '#ffc107',
            'Sheds': '#20c997',
            'Storage Zones': '#dc3545',
            'Recreation Areas': '#f8f9fa'
        }
        
        logger.info("地图生成器初始化完成")
    
    def generate(self, geojson_path: str, output_path: str) -> str:
        """
        从GeoJSON文件生成HTML地图
        
        Args:
            geojson_path: GeoJSON文件路径
            output_path: HTML输出路径
            
        Returns:
            生成的HTML文件路径
        """
        try:
            # 读取GeoJSON数据
            with open(geojson_path, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
            
            # 生成HTML
            return self.generate_from_data(geojson_data, output_path)
            
        except Exception as e:
            logger.error(f"生成地图失败: {e}")
            return ""
    
    def generate_from_data(
        self, 
        geojson_data: Dict[str, Any], 
        output_path: str
    ) -> str:
        """
        从GeoJSON数据生成HTML地图
        
        Args:
            geojson_data: GeoJSON数据字典
            output_path: HTML输出路径
            
        Returns:
            生成的HTML文件路径
        """
        try:
            # 计算地图边界和中心
            center_lat, center_lon, zoom_level = self._calculate_map_center(geojson_data)
            
            # 生成HTML内容
            html_content = self._generate_html_content(
                geojson_data, 
                center_lat, 
                center_lon, 
                zoom_level
            )
            
            # 写入文件
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"✓ 生成HTML地图: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"生成地图失败: {e}")
            return ""
    
    def _calculate_map_center(
        self, 
        geojson_data: Dict[str, Any]
    ) -> tuple:
        """
        计算地图中心和缩放级别
        
        Args:
            geojson_data: GeoJSON数据
            
        Returns:
            (center_lat, center_lon, zoom_level)
        """
        features = geojson_data.get('features', [])
        
        if not features:
            return (23.0, 114.0, 12)  # 默认深圳地区
        
        # 提取所有中心点坐标
        lats = []
        lons = []
        
        for feature in features:
            props = feature.get('properties', {})
            if 'center_lat' in props and 'center_lon' in props:
                lats.append(props['center_lat'])
                lons.append(props['center_lon'])
        
        if not lats or not lons:
            return (23.0, 114.0, 12)
        
        # 计算中心点
        center_lat = (min(lats) + max(lats)) / 2
        center_lon = (min(lons) + max(lons)) / 2
        
        # 根据范围估算缩放级别
        lat_range = max(lats) - min(lats)
        lon_range = max(lons) - min(lons)
        max_range = max(lat_range, lon_range)
        
        # 简单的缩放级别估算
        if max_range < 0.001:
            zoom_level = 18  # 很小的区域
        elif max_range < 0.01:
            zoom_level = 15
        elif max_range < 0.05:
            zoom_level = 13
        else:
            zoom_level = 11
        
        return (center_lat, center_lon, zoom_level)
    
    def _generate_html_content(
        self,
        geojson_data: Dict[str, Any],
        center_lat: float,
        center_lon: float,
        zoom_level: int
    ) -> str:
        """
        生成HTML内容
        
        Args:
            geojson_data: GeoJSON数据
            center_lat: 地图中心纬度
            center_lon: 地图中心经度
            zoom_level: 缩放级别
            
        Returns:
            HTML字符串
        """
        geojson_str = json.dumps(geojson_data, ensure_ascii=False)
        colors_str = json.dumps(self.class_colors, ensure_ascii=False)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>石马河四乱检测结果可视化</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ 
            margin: 0; 
            padding: 0; 
            font-family: 'Segoe UI', 'Microsoft YaHei', Arial, sans-serif; 
        }}
        #map {{ height: 100vh; width: 100%; }}
        
        .info-panel {{
            position: absolute; 
            top: 10px; 
            right: 10px;
            background: white; 
            padding: 20px; 
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2); 
            z-index: 1000; 
            max-width: 320px;
            min-width: 250px;
        }}
        
        .info-panel h3 {{ 
            margin-top: 0; 
            font-size: 18px; 
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }}
        
        .info-panel .stat-item {{
            display: flex;
            justify-content: space-between;
            margin: 8px 0;
            font-size: 14px;
        }}
        
        .info-panel .stat-label {{
            color: #666;
        }}
        
        .info-panel .stat-value {{
            font-weight: bold;
            color: #007bff;
        }}
        
        .legend {{
            position: absolute; 
            bottom: 30px; 
            right: 10px;
            background: white; 
            padding: 15px; 
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2); 
            z-index: 1000;
            max-height: 400px;
            overflow-y: auto;
        }}
        
        .legend h4 {{
            margin: 0 0 10px 0;
            font-size: 16px;
            color: #333;
        }}
        
        .legend-item {{ 
            display: flex; 
            align-items: center; 
            margin: 8px 0; 
            font-size: 13px; 
        }}
        
        .legend-color {{ 
            width: 24px; 
            height: 24px; 
            margin-right: 10px; 
            border: 2px solid #333;
            border-radius: 3px;
        }}
        
        .leaflet-popup-content {{
            font-size: 13px;
            line-height: 1.6;
        }}
        
        .leaflet-popup-content strong {{
            color: #007bff;
            font-size: 15px;
        }}
        
        .popup-field {{
            margin: 5px 0;
            display: flex;
            justify-content: space-between;
        }}
        
        .popup-label {{
            color: #666;
            min-width: 100px;
        }}
        
        .popup-value {{
            font-weight: 500;
            text-align: right;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    
    <div class="info-panel">
        <h3>🚁 无人机检测结果</h3>
        <div class="stat-item">
            <span class="stat-label">总检测数:</span>
            <span class="stat-value" id="total-count">0</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">坐标系:</span>
            <span class="stat-value">CGCS2000</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">数据状态:</span>
            <span class="stat-value" id="data-status">已加载</span>
        </div>
        <hr style="margin: 15px 0; border: none; border-top: 1px solid #ddd;">
        <p style="font-size: 12px; color: #666; margin: 0;">
            💡 点击检测框查看详情<br>
            📊 使用图例筛选类别
        </p>
    </div>
    
    <div class="legend">
        <h4>📍 检测类别图例</h4>
        <div id="legend-items"></div>
    </div>
    
    <script>
        // 初始化地图
        var map = L.map('map').setView([{center_lat}, {center_lon}], {zoom_level});
        
        // 添加天地图底图（中国地区推荐）
        // 备选：OpenStreetMap
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }}).addTo(map);
        
        // 加载GeoJSON数据
        var geojsonData = {geojson_str};
        var classColors = {colors_str};
        
        // 样式函数
        function getStyle(feature) {{
            var props = feature.properties;
            var className = props.class_name || 'unknown';
            var color = classColors[className] || '#6c757d';
            
            // 根据置信度调整透明度
            var confidence = props.confidence || 0.5;
            var fillOpacity = 0.3 + confidence * 0.4;
            
            return {{
                fillColor: color,
                weight: 2,
                opacity: 1,
                color: color,
                fillOpacity: fillOpacity
            }};
        }}
        
        // 弹窗内容生成
        function onEachFeature(feature, layer) {{
            if (feature.properties) {{
                var p = feature.properties;
                var popupContent = '<div style="min-width: 250px;">';
                
                // 标题
                popupContent += '<strong>' + p.class_name + '</strong><br>';
                popupContent += '<hr style="margin: 8px 0; border-color: #ddd;">';
                
                // 基本信息
                popupContent += '<div class="popup-field">';
                popupContent += '<span class="popup-label">置信度:</span>';
                popupContent += '<span class="popup-value">' + (p.confidence * 100).toFixed(1) + '%</span>';
                popupContent += '</div>';
                
                popupContent += '<div class="popup-field">';
                popupContent += '<span class="popup-label">帧号:</span>';
                popupContent += '<span class="popup-value">' + p.frame_number + '</span>';
                popupContent += '</div>';
                
                if (p.datetime) {{
                    popupContent += '<div class="popup-field">';
                    popupContent += '<span class="popup-label">时间:</span>';
                    popupContent += '<span class="popup-value">' + p.datetime + '</span>';
                    popupContent += '</div>';
                }}
                
                // GPS坐标
                popupContent += '<hr style="margin: 8px 0; border-color: #ddd;">';
                popupContent += '<div class="popup-field">';
                popupContent += '<span class="popup-label">纬度:</span>';
                popupContent += '<span class="popup-value">' + p.center_lat.toFixed(6) + '</span>';
                popupContent += '</div>';
                
                popupContent += '<div class="popup-field">';
                popupContent += '<span class="popup-label">经度:</span>';
                popupContent += '<span class="popup-value">' + p.center_lon.toFixed(6) + '</span>';
                popupContent += '</div>';
                
                popupContent += '<div class="popup-field">';
                popupContent += '<span class="popup-label">高度:</span>';
                popupContent += '<span class="popup-value">' + p.altitude.toFixed(1) + 'm</span>';
                popupContent += '</div>';
                
                // GPS质量信息（如果有）
                if (p.gps_quality) {{
                    popupContent += '<hr style="margin: 8px 0; border-color: #ddd;">';
                    popupContent += '<div class="popup-field">';
                    popupContent += '<span class="popup-label">GPS质量:</span>';
                    popupContent += '<span class="popup-value">' + p.gps_quality + '</span>';
                    popupContent += '</div>';
                    
                    if (p.positioning_state) {{
                        popupContent += '<div class="popup-field">';
                        popupContent += '<span class="popup-label">定位状态:</span>';
                        popupContent += '<span class="popup-value">' + p.positioning_state + '</span>';
                        popupContent += '</div>';
                    }}
                    
                    if (p.estimated_error !== undefined) {{
                        var errorColor = p.estimated_error < 5 ? '#28a745' : (p.estimated_error < 10 ? '#ffc107' : '#dc3545');
                        popupContent += '<div class="popup-field">';
                        popupContent += '<span class="popup-label">预估误差:</span>';
                        popupContent += '<span class="popup-value" style="color: ' + errorColor + '">';
                        popupContent += '±' + p.estimated_error.toFixed(2) + 'm</span>';
                        popupContent += '</div>';
                    }}
                    
                    if (p.satellite_count) {{
                        popupContent += '<div class="popup-field">';
                        popupContent += '<span class="popup-label">卫星数:</span>';
                        popupContent += '<span class="popup-value">' + p.satellite_count + '</span>';
                        popupContent += '</div>';
                    }}
                }}
                
                // 边缘标记
                if (p.is_on_edge) {{
                    popupContent += '<hr style="margin: 8px 0; border-color: #ddd;">';
                    popupContent += '<div style="color: #ffc107; font-size: 12px;">';
                    popupContent += '⚠️ 边缘检测: ' + (p.edge_positions || '未知');
                    popupContent += '</div>';
                }}
                
                popupContent += '</div>';
                
                layer.bindPopup(popupContent, {{
                    maxWidth: 300,
                    className: 'custom-popup'
                }});
            }}
        }}
        
        // 添加GeoJSON图层
        var geojsonLayer = L.geoJSON(geojsonData, {{
            style: getStyle,
            onEachFeature: onEachFeature
        }}).addTo(map);
        
        // 自适应边界
        if (geojsonData.features.length > 0) {{
            map.fitBounds(geojsonLayer.getBounds(), {{padding: [50, 50]}});
        }}
        
        // 更新统计信息
        document.getElementById('total-count').textContent = geojsonData.features.length;
        
        // 生成图例
        var classSet = new Set();
        var classCounts = {{}};
        
        geojsonData.features.forEach(function(f) {{
            var className = f.properties.class_name;
            classSet.add(className);
            classCounts[className] = (classCounts[className] || 0) + 1;
        }});
        
        var legendItems = document.getElementById('legend-items');
        Array.from(classSet).sort().forEach(function(className) {{
            var color = classColors[className] || '#6c757d';
            var count = classCounts[className];
            
            var item = document.createElement('div');
            item.className = 'legend-item';
            item.innerHTML = '<div class="legend-color" style="background-color: ' + color + '"></div>' +
                           '<span>' + className + ' (' + count + ')</span>';
            legendItems.appendChild(item);
        }});
        
        console.log('地图加载完成:', geojsonData.features.length, '个检测结果');
    </script>
</body>
</html>"""
        
        return html
