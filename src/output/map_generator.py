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
        
        # 地图样式配置 — 与 yolo_config.yaml classes.names 对应
        self.class_colors = {
            '无': '#adb5bd',
            '围垦湖泊': '#0d6efd',
            '非法侵占水域': '#0dcaf0',
            '阻碍行洪作物': '#198754',
            '未依法批准围垦河道': '#6610f2',
            '围占养殖': '#6f42c1',
            '围网养殖': '#d63384',
            '坑塘养殖': '#20c997',
            '文体旅游项目': '#ffc107',
            '耕地': '#2ecc71',
            '片林': '#27ae60',
            '其他占用': '#e67e22',
            '非法采砂': '#e74c3c',
            '取土取石': '#c0392b',
            '在禁采区、禁采期采砂': '#a93226',
            '不按许可要求采砂': '#cb4335',
            '其他开采': '#d35400',
            '弃渣（土）场': '#8e44ad',
            '垃圾堆放': '#fd7e14',
            '固体废物': '#e83e8c',
            '其他堆放': '#f39c12',
            '弃置、堆放阻碍行洪的物体': '#dc3545',
            '阻碍行洪建筑物': '#c62828',
            '未经许可涉河项目': '#ad1457',
            '修建阻碍行洪的建筑物、构筑物': '#b71c1c',
            '临河房屋': '#1976d2',
            '码头': '#00838f',
            '造（修）船厂': '#00695c',
            '光伏电厂': '#ff8f00',
            '砖瓦窑厂': '#795548',
            '大棚': '#43a047',
            '桥梁': '#546e7a',
            '在建桥梁': '#78909c',
            '拦河闸坝': '#5c6bc0',
            '在建拦河闸坝': '#7986cb',
            '其他建（构）筑物': '#8d6e63',
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
            
            # 将 image_path 转为相对于 map.html 的路径
            self._resolve_image_paths(geojson_data, output_path)
            
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
    
    def _resolve_image_paths(
        self,
        geojson_data: Dict[str, Any],
        output_path: str
    ):
        """将 GeoJSON 中的 image_path 转为相对于 map.html 输出目录的路径"""
        map_dir = os.path.dirname(os.path.abspath(output_path))
        
        for feature in geojson_data.get('features', []):
            props = feature.get('properties', {})
            img_path = props.get('image_path', '')
            if not img_path:
                continue
            try:
                abs_img = os.path.abspath(img_path)
                rel_path = os.path.relpath(abs_img, map_dir)
                props['image_path'] = rel_path.replace('\\', '/')
            except (ValueError, TypeError):
                pass
    
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
        
        .popup-image {{
            width: 100%;
            max-height: 300px;
            object-fit: contain;
            border-radius: 4px;
            border: 1px solid #ddd;
            margin: 8px 0;
            cursor: pointer;
            background: #f5f5f5;
        }}
        
        .popup-image:hover {{
            border-color: #007bff;
        }}
        
        .popup-no-image {{
            color: #999;
            font-size: 12px;
            text-align: center;
            padding: 10px;
            background: #f9f9f9;
            border-radius: 4px;
            margin: 8px 0;
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
        
        // 底图图层
        var satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            attribution: '&copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
            maxZoom: 19
        }});
        
        var osmLayer = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }});
        
        // 卫星图标注叠加层（地名、道路名）
        var labels = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_only_labels/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; CARTO',
            maxZoom: 19,
            subdomains: 'abcd',
            pane: 'shadowPane'
        }});
        
        // 默认使用卫星底图 + 标注
        satellite.addTo(map);
        labels.addTo(map);
        
        // 图层切换控件
        var baseMaps = {{
            "卫星地图": satellite,
            "街道地图": osmLayer
        }};
        var overlayMaps = {{
            "地名标注": labels
        }};
        L.control.layers(baseMaps, overlayMaps, {{position: 'topleft'}}).addTo(map);
        
        // 加载GeoJSON数据
        var geojsonData = {geojson_str};
        var classColors = {colors_str};
        
        // 基于字符串哈希生成 HSL 颜色（用于未预定义的类别）
        function hashColor(str) {{
            var h = 0;
            for (var i = 0; i < str.length; i++) {{
                h = str.charCodeAt(i) + ((h << 5) - h);
            }}
            var hue = ((h % 360) + 360) % 360;
            return 'hsl(' + hue + ', 70%, 50%)';
        }}
        
        // 样式函数
        function getStyle(feature) {{
            var props = feature.properties;
            var className = props.class_name || 'unknown';
            var color = classColors[className] || hashColor(className);
            
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
                
                // 检测截图
                if (p.image_path && p.image_path.length > 0) {{
                    popupContent += '<a href="' + p.image_path + '" target="_blank" title="点击查看原图">';
                    popupContent += '<img class="popup-image" src="' + p.image_path + '" ';
                    popupContent += 'onerror="this.parentElement.outerHTML=\\'<div class=popup-no-image>截图未找到</div>\\'" />';
                    popupContent += '</a>';
                }}
                
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
                    maxWidth: 450,
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
            var color = classColors[className] || hashColor(className);
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
