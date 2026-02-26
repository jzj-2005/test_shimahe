# GeoJSON和地图输出使用指南

**版本**: v2.1.0  
**更新日期**: 2026-02-25  
**适用用户**: 系统操作员、GIS技术人员、项目管理人员

---

## 快速开始

### 30秒了解新功能

v2.1版本后，运行检测时会**自动生成**：

✅ CSV原始数据（所有检测）  
✅ GeoJSON矢量数据（去重后，可导入GIS）  
✅ HTML交互式地图（浏览器查看）  
✅ 统计摘要（数据分析）

**不需要手动运行任何额外脚本！**

---

## 一、自动输出功能

### 1.1 运行检测

**离线模式**：

```bash
python src/main.py --mode offline --video test.mp4
```

**实时模式**：

```bash
python run_realtime.py
# 运行一段时间后按ESC退出
```

### 1.2 自动输出清单

检测完成后，在 `data/output/` 目录下自动生成：

| 文件 | 说明 | 推荐用途 |
|------|------|---------|
| `csv/detections_offline.csv` | CSV原始数据（所有检测） | Excel查看、数据分析 |
| `geojson/detections_raw.geojson` | GeoJSON原始数据 | 审计、完整记录 |
| **`geojson/detections_unique.geojson`** | **GeoJSON去重数据（推荐）** | **GIS展示、汇报** |
| `geojson/detections_high_conf.geojson` | 高置信度数据 | 重点区域标注 |
| **`map.html`** | **交互式地图** | **快速预览、演示** |
| `summary.txt` | 统计摘要 | 数据概览 |

---

## 二、查看和使用输出文件

### 2.1 快速预览：HTML地图

**最简单的查看方式！**

**Windows**：

```bash
# 双击打开
start data/output/map.html

# 或直接双击文件
```

**功能说明**：

- 🗺️ 在OpenStreetMap上显示所有检测结果
- 🎨 不同类别用不同颜色（违建=红色、垃圾=橙色等）
- 📊 透明度反映置信度（高置信度更明显）
- 🖱️ 点击检测框查看详细信息：
  - 类别名称、置信度、帧号
  - GPS坐标（纬度、经度、高度）
  - GPS质量（RTK/HIGH/MEDIUM）
  - 定位误差（±X米）
  - 边缘标记
- 📍 右侧图例显示类别和数量
- 🔍 支持缩放、平移、测距

### 2.2 GIS软件使用

#### 方法1：QGIS（推荐，免费开源）

**步骤1：打开QGIS**

**步骤2：添加矢量图层**

```
菜单: 图层 → 添加图层 → 添加矢量图层...
或: Ctrl+Shift+V
```

**步骤3：选择文件**

```
文件路径: d:\jzj\siluan_new\data\output\geojson\detections_unique.geojson
```

**步骤4：设置样式**

- 右键图层 → 属性 → 符号系统
- 选择"分类"，字段选择 `class_name`
- 点击"分类"按钮自动按类别着色

**步骤5：查看属性**

- 点击工具栏的"识别要素"工具
- 点击地图上的检测框
- 查看所有属性（置信度、GPS质量等）

#### 方法2：ArcGIS Pro

**步骤1：打开ArcGIS Pro**

**步骤2：添加数据**

```
工具栏: Add Data → 选择 detections_unique.geojson
```

**步骤3：设置符号系统**

```
右键图层 → Symbology → Unique Values → Field: class_name
```

#### 方法3：Google Earth Pro

GeoJSON需要先转换为KML：

```bash
# 使用在线工具转换
# https://mygeodata.cloud/converter/geojson-to-kml

# 或使用QGIS导出
# 右键图层 → 导出 → 保存要素为... → KML格式
```

### 2.3 Excel/WPS查看CSV

**直接打开**：

```bash
# 双击CSV文件
data/output/csv/detections_offline.csv
```

**查看内容**：

- 所有检测的原始数据（包括重复检测）
- 可筛选、排序、分析
- 包含完整GPS质量信息

**注意**：

- Excel打开CSV时，不要保存（避免格式损坏）
- 大文件（>5000行）建议用专业工具（如Pandas）

### 2.4 查看统计摘要

**打开文件**：

```bash
notepad data/output/summary.txt
```

**内容包括**：

```
============================================================
石马河四乱检测系统 - 检测结果统计摘要
============================================================

## 1. 数据概览
--------------------------------------------------------------------
原始检测总数: 523 条
去重后数量: 156 条
去除重复: 367 条 (70.2%)

## 2. 按类别统计
--------------------------------------------------------------------
  违建                  :    45 ( 28.8%)
  垃圾                  :    38 ( 24.4%)
  污水                  :    35 ( 22.4%)
  违种                  :    38 ( 24.4%)

## 3. 置信度统计
--------------------------------------------------------------------
  平均置信度: 0.782
  最高置信度: 0.954
  最低置信度: 0.512
  中位数置信度: 0.786

## 4. 地理坐标范围
--------------------------------------------------------------------
  纬度范围: 22.779500 ~ 22.781200
  经度范围: 114.100500 ~ 114.102800
  高度范围: 135.2m ~ 142.8m
  覆盖范围: 约 188m × 256m

## 5. GPS质量统计
--------------------------------------------------------------------
  RTK               :    89 ( 57.1%)
  HIGH              :    45 ( 28.8%)
  MEDIUM            :    22 ( 14.1%)

  平均定位误差: 2.35m
  最大定位误差: 8.50m

## 6. 边缘检测统计
--------------------------------------------------------------------
  边缘检测数: 34 (21.8%)
  完整检测数: 122 (78.2%)
```

---

## 三、配置指南

### 3.1 离线模式配置（推荐）

**文件**: `config/offline_config.yaml`

**完全自动化配置**（推荐）：

```yaml
output:
  # GeoJSON导出
  export_geojson: true             # 开启自动导出
  
  # 智能去重
  enable_deduplication: true       # 开启去重
  deduplication:
    distance_threshold: 5.0        # 5米内视为同一目标
    prefer_non_edge: true          # 优先保留中央检测
    prefer_rtk: true               # 优先保留RTK定位
    min_quality_score: 0.3         # 过滤低质量检测
  
  # 地图生成
  generate_map: true               # 开启地图生成
  auto_open_map: true              # 处理完自动打开（方便查看）
  
  # 统计摘要
  generate_summary: true           # 开启摘要生成
```

**修改后重新运行**：

```bash
python src/main.py --mode offline --video test.mp4
# 检测完成后自动打开地图！
```

### 3.2 实时模式配置（谨慎）

**文件**: `config/realtime_config.yaml`

**短时运行配置**（<30分钟）：

```yaml
output:
  export_geojson: true             # 可以开启
  enable_deduplication: true       # 必须开启去重
  generate_map: true               # 可以开启
  auto_open_map: false             # 建议关闭
  generate_summary: true
```

**长时运行配置**（>1小时）：

```yaml
output:
  export_geojson: false            # 建议关闭（数据量大）
  enable_deduplication: true       # 如果开启GeoJSON必须启用
  generate_map: false              # 建议关闭
  auto_open_map: false
  generate_summary: true           # 建议开启
```

### 3.3 调试模式配置

**查看所有原始数据**（不去重）：

```yaml
output:
  export_geojson: true
  enable_deduplication: false      # 关闭去重
  generate_map: true
```

**提高去重严格度**：

```yaml
deduplication:
  distance_threshold: 3.0          # 从5米改为3米（更严格）
  min_quality_score: 0.5           # 从0.3提高到0.5
```

**降低去重严格度**：

```yaml
deduplication:
  distance_threshold: 10.0         # 从5米改为10米（更宽松）
  min_quality_score: 0.2           # 从0.3降低到0.2
```

---

## 四、使用场景和示例

### 4.1 场景1：日常巡检报告

**需求**：每天巡检一次，生成检测报告提交

**配置**：

```yaml
output:
  export_geojson: true
  enable_deduplication: true
  generate_map: true
  auto_open_map: true              # 处理完自动打开查看
```

**工作流**：

1. 运行检测
2. 检测完成后地图自动打开
3. 快速查看检测结果
4. 打开 `summary.txt` 查看统计数据
5. 将 `detections_unique.geojson` 导入GIS系统存档

### 4.2 场景2：应急响应

**需求**：发现异常情况，需要快速定位和上报

**配置**：

```yaml
output:
  export_geojson: true
  generate_map: true
  auto_open_map: true              # 立即查看
  geojson_high_confidence: 0.8     # 只关注高置信度
```

**工作流**：

1. 实时模式运行，发现目标
2. 按ESC停止
3. 地图自动打开，快速定位异常
4. 截图或导出 `detections_high_conf.geojson`
5. 上报给相关部门

### 4.3 场景3：数据分析和研究

**需求**：分析检测数据，研究目标分布规律

**配置**：

```yaml
output:
  export_geojson: true
  enable_deduplication: false      # 关闭去重，保留完整数据
  generate_map: true
  generate_summary: true
```

**工作流**：

1. 运行检测
2. 在QGIS中加载 `detections_raw.geojson`
3. 使用QGIS的分析工具：
   - 热力图分析
   - 密度分析
   - 空间统计
4. 查看 `summary.txt` 了解整体情况

### 4.4 场景4：项目交付

**需求**：向甲方交付检测成果

**配置**：

```yaml
output:
  export_geojson: true
  enable_deduplication: true
  generate_map: true
  generate_summary: true
```

**交付清单**：

```
交付文件夹/
├── 1_检测报告/
│   ├── detections_unique.geojson       # GIS矢量数据
│   ├── map.html                        # 可视化地图
│   └── summary.txt                     # 统计摘要
├── 2_原始数据/
│   ├── detections_offline.csv          # CSV完整数据
│   └── detections_raw.geojson          # GeoJSON原始数据
├── 3_检测截图/
│   └── images/                         # 所有检测截图
└── 4_系统文档/
    ├── README.md                       # 系统说明
    └── GeoJSON和地图输出使用指南.md    # 本文档
```

---

## 五、功能详解

### 5.1 智能去重功能

#### 什么是去重？

**问题**：实时模式下，无人机飞过一个目标时，会连续检测几十到上百次：

```
帧1: 发现违建 (边缘位置，50%可见)
帧2: 发现违建 (边缘位置，60%可见)
帧5: 发现违建 (中央位置，100%可见) ← 最佳检测
帧8: 发现违建 (中央位置，95%可见)
帧12: 发现违建 (边缘位置，40%可见)
...
```

结果：同一个违建有100条记录！

**解决**：智能去重保留**质量最好**的那一条（第5帧）

#### 去重原理

**步骤1：空间分组**

- 计算所有检测之间的GPS距离
- 距离<5米的归为同一组（同一目标）

**步骤2：质量评分**

为每个检测打分，考虑：

| 因素 | 权重 | 说明 |
|------|------|------|
| 置信度 | 基础分 | 0.5-1.0 |
| 边缘位置 | ×0.5 | 边缘目标可能不完整 |
| GPS质量 | ×0.7-1.2 | RTK更可靠 |
| 定位误差 | ×0.8-1.0 | 误差大的降权 |

**步骤3：选择最佳**

每组保留质量评分最高的检测

#### 效果对比

**示例：5分钟离线视频**

| 指标 | 去重前 | 去重后 | 改善 |
|------|--------|--------|------|
| 检测记录数 | 523 | 156 | ↓ 70% |
| CSV文件大小 | 156KB | 47KB | ↓ 70% |
| GeoJSON大小 | 380KB | 120KB | ↓ 68% |
| 地图加载速度 | 2.5s | 0.8s | ↑ 3倍 |
| 数据可读性 | 密集重叠 | 清晰明了 | 显著提升 |

**示例：1小时实时流**

| 指标 | 去重前 | 去重后 | 改善 |
|------|--------|--------|------|
| 检测记录数 | 18,234 | 587 | ↓ 97% |
| GeoJSON大小 | 3.8MB | 145KB | ↓ 96% |

#### 配置调整

**更严格的去重**（减少更多）：

```yaml
deduplication:
  distance_threshold: 3.0          # 从5米改为3米
  min_quality_score: 0.5           # 从0.3提高到0.5
```

**更宽松的去重**（保留更多）：

```yaml
deduplication:
  distance_threshold: 10.0         # 从5米改为10米
  min_quality_score: 0.2           # 从0.3降低到0.2
```

**完全关闭去重**（查看所有原始数据）：

```yaml
output:
  enable_deduplication: false
```

### 5.2 GeoJSON文件说明

#### 三个版本的区别

| 文件 | 数据来源 | 数据量 | 推荐用途 |
|------|---------|--------|---------|
| `detections_raw.geojson` | CSV所有记录 | 最大 | 审计、完整记录、数据分析 |
| `detections_unique.geojson` | 智能去重后 | 中等 | **GIS展示、汇报演示** |
| `detections_high_conf.geojson` | 去重+高置信度 | 最小 | 重点关注区域、高精度标注 |

#### 文件格式

- **格式**: GeoJSON (RFC 7946)
- **编码**: UTF-8
- **坐标系**: CGCS2000 (EPSG:4490)
- **几何类型**: Polygon（多边形）
- **坐标顺序**: [经度, 纬度] ⚠️

#### 属性字段

每个检测包含以下属性：

| 属性 | 说明 | 示例 |
|------|------|------|
| `class_name` | 检测类别 | "违建" |
| `confidence` | 置信度 | 0.92 |
| `center_lat` | 中心纬度 | 22.779814 |
| `center_lon` | 中心经度 | 114.101319 |
| `altitude` | 飞行高度 | 139.2 |
| `gps_quality` | GPS质量 | "RTK" |
| `estimated_error` | 定位误差 | 0.05 |
| `is_on_edge` | 边缘标记 | false |
| `frame_number` | 帧号 | 45 |
| `datetime` | 时间 | "2026-02-10 10:30:15" |
| `image_path` | 截图路径 | "./data/output/images/..." |

### 5.3 HTML地图说明

#### 地图组成

```
map.html 文件包含：
- HTML结构
- CSS样式
- JavaScript代码
- 内联GeoJSON数据
```

**优点**：
- ✅ 单文件，易于分享
- ✅ 无需服务器，双击即可打开
- ✅ 支持所有现代浏览器

#### 地图操作

| 操作 | 说明 |
|------|------|
| **拖动** | 平移地图 |
| **滚轮** | 缩放地图 |
| **点击检测框** | 显示详细信息弹窗 |
| **双击** | 快速放大 |
| **Shift+拖动** | 框选缩放区域 |

#### 地图元素

1. **信息面板**（右上角）
   - 总检测数
   - 坐标系说明
   - 操作提示

2. **图例**（右下角）
   - 类别名称
   - 颜色标识
   - 数量统计

3. **检测框**
   - 多边形显示
   - 颜色区分类别
   - 透明度反映置信度

---

## 六、常见问题

### Q1: 检测完成后没有生成GeoJSON？

**排查步骤**：

1. **检查配置文件**
   ```yaml
   # config/offline_config.yaml
   output:
     export_geojson: true  # 确认是否为true
   ```

2. **检查日志输出**
   ```
   [INFO] 开始后处理...
   [INFO] 读取检测数据: X 条记录
   ```
   - 如果没有这些日志，说明后处理未触发

3. **检查CSV是否有数据**
   ```bash
   # 查看CSV文件大小
   ls -lh data/output/csv/detections_offline.csv
   ```
   - 如果CSV为空，不会生成GeoJSON

4. **检查输出目录权限**
   ```bash
   # 确保可以创建文件
   mkdir data/output/geojson/
   ```

### Q2: 地图打不开或显示空白？

**解决方法**：

1. **检查浏览器**
   - 建议使用Chrome、Firefox、Edge
   - 避免使用IE浏览器

2. **检查文件路径**
   - 确保路径中没有中文或特殊字符
   - 可以把 `map.html` 复制到桌面打开

3. **检查网络**
   - 地图需要加载Leaflet.js（CDN）
   - 如果内网环境，可能需要配置本地Leaflet

4. **查看浏览器控制台**
   - F12打开开发者工具
   - 查看Console标签页的错误信息

### Q3: 去重后数据太少？

**原因分析**：

可能是配置太严格了，尝试放宽：

```yaml
deduplication:
  distance_threshold: 10.0         # 从5米增加到10米
  min_quality_score: 0.2           # 从0.3降低到0.2
  prefer_non_edge: false           # 不区分边缘和中央
```

### Q4: 去重后数据还是太多？

**原因分析**：

可能是距离阈值太大或质量阈值太低：

```yaml
deduplication:
  distance_threshold: 3.0          # 从5米减少到3米
  min_quality_score: 0.5           # 从0.3提高到0.5
```

### Q5: 如何在ArcGIS Online中使用？

**步骤**：

1. 登录 ArcGIS Online
2. 内容 → 添加项目 → 从文件
3. 选择 `detections_unique.geojson`
4. 设置符号系统和弹窗
5. 分享地图链接

### Q6: 可以导出为Shapefile吗？

**方法1：使用QGIS**

```
1. 在QGIS中加载 detections_unique.geojson
2. 右键图层 → 导出 → 保存要素为...
3. 格式选择"ESRI Shapefile"
4. 设置输出路径
5. 确定
```

**方法2：使用ogr2ogr命令**

```bash
ogr2ogr -f "ESRI Shapefile" output.shp detections_unique.geojson
```

### Q7: 后处理耗时太长？

**优化建议**：

1. **关闭不需要的功能**
   ```yaml
   generate_map: false  # 如果不需要地图
   ```

2. **提高质量阈值**
   ```yaml
   min_quality_score: 0.5  # 过滤更多低质量检测
   ```

3. **限制处理数据量**
   - 离线模式：缩短视频长度
   - 实时模式：缩短运行时间

---

## 七、最佳实践

### 7.1 推荐配置

**离线模式**（推荐配置）：

```yaml
output:
  # 开启所有功能
  export_geojson: true
  enable_deduplication: true
  generate_map: true
  auto_open_map: true              # 自动打开方便查看
  generate_summary: true
  
  # 合理的去重参数
  deduplication:
    distance_threshold: 5.0        # 5米阈值平衡效果
    min_quality_score: 0.3         # 过滤明显低质量
```

**实时模式**（谨慎配置）：

```yaml
output:
  # 按需开启
  export_geojson: false            # 默认关闭
  enable_deduplication: true       # 必须开启
  generate_map: false              # 默认关闭
  generate_summary: true           # 建议开启
```

### 7.2 工作流程建议

**每日巡检流程**：

```
上午：
1. 启动实时检测（关闭GeoJSON生成，降低开销）
2. 巡检作业
3. 按ESC停止，查看summary.txt统计

下午（如发现异常）：
1. 运行离线处理对可疑区域视频重新分析
2. 开启所有输出功能
3. 生成完整报告（CSV + GeoJSON + 地图）
4. 提交给相关部门
```

### 7.3 数据管理建议

**目录组织**：

```
data/
├── input/                   # 输入数据
│   └── videos/
│       ├── 2026-02-25/      # 按日期组织
│       └── 2026-02-26/
└── output/
    ├── 2026-02-25/          # 按日期归档
    │   ├── csv/
    │   ├── geojson/
    │   └── map.html
    └── 2026-02-26/
```

**备份策略**：

- CSV和GeoJSON：长期保存
- 截图：按需保留（占空间大）
- 地图：可随时重新生成

---

## 八、故障排查

### 8.1 后处理未执行

**症状**：检测完成后没有生成GeoJSON和地图

**检查清单**：

- [ ] 配置文件中 `export_geojson: true`
- [ ] CSV文件存在且有数据
- [ ] 程序正常结束（不是强制终止）
- [ ] 查看日志是否有错误信息

### 8.2 去重效果不理想

**症状1：去重后还是太多重复**

**解决**：减小距离阈值

```yaml
distance_threshold: 3.0  # 从5米改为3米
```

**症状2：明显不同的目标被合并了**

**解决**：增大距离阈值

```yaml
distance_threshold: 10.0  # 从5米改为10米
```

### 8.3 地图加载慢

**原因**：数据量太大

**解决**：

1. **开启去重**
   ```yaml
   enable_deduplication: true
   ```

2. **提高质量阈值**
   ```yaml
   min_quality_score: 0.5
   ```

3. **只使用高置信度数据生成地图**
   - 手动用 `detections_high_conf.geojson` 生成地图

---

## 九、进阶使用

### 9.1 自定义地图样式

**修改文件**: `src/output/map_generator.py`

**修改类别颜色**：

```python
self.class_colors = {
    '违建': '#ff0000',      # 改为纯红色
    '垃圾': '#ffa500',      # 改为橙色
    # ... 自定义其他颜色
}
```

**修改底图**：

```python
# 改为天地图
L.tileLayer('http://t{s}.tianditu.gov.cn/vec_w/wmts?...')

# 改为高德地图
L.tileLayer('http://webrd0{s}.is.autonavi.com/appmaptile?...')
```

### 9.2 批量处理多个视频

**脚本示例**：

```bash
# batch_process.bat

@echo off
for %%f in (data\input\videos\*.mp4) do (
    echo 处理: %%f
    python src/main.py --mode offline --video "%%f"
    
    REM 重命名输出文件
    set filename=%%~nf
    move data\output\map.html "data\output\!filename!_map.html"
    move data\output\summary.txt "data\output\!filename!_summary.txt"
)

echo 批量处理完成！
```

### 9.3 定期自动巡检

**Windows计划任务**：

```bash
# 1. 创建批处理脚本 auto_patrol.bat
cd d:\jzj\siluan_new
python run_realtime.py
timeout /t 3600  # 运行1小时
taskkill /IM python.exe /F  # 强制停止

# 2. 添加到Windows计划任务
# 计划任务 → 创建基本任务 → 设置每天8:00运行
```

---

## 十、技术支持

### 10.1 日志查看

**日志位置**：

- 离线模式：`data/output/offline_log.txt`
- 实时模式：`data/output/realtime_log.txt`

**关键日志**：

```
[INFO] 开始后处理...
[INFO] 读取检测数据: 523 条记录
[INFO] 去重完成: 523 -> 156 条
[INFO] ✓ 导出原始GeoJSON: ... (523条)
[INFO] ✓ 导出去重GeoJSON: ... (156条)
[INFO] ✓ 生成HTML地图: ...
[INFO] ✓ 后处理完成
```

### 10.2 手动生成（备用方法）

如果自动生成失败，可以手动运行工具：

**生成GeoJSON**：

```bash
python tools/export_to_geojson.py data/output/csv/detections_offline.csv
```

**生成地图**：

```bash
python tools/quick_visualize.py data/output/geojson/detections.geojson
```

---

## 十一、总结

### 11.1 功能特点

✅ **全自动**：检测完成后自动生成所有输出  
✅ **智能去重**：保留最佳质量检测，数据量减少70-97%  
✅ **多格式输出**：CSV、GeoJSON、HTML地图、统计摘要  
✅ **GIS兼容**：符合CGCS2000标准，可导入主流GIS软件  
✅ **可配置**：所有功能都可通过配置文件控制  
✅ **向后兼容**：不影响现有工作流程

### 11.2 快速检查表

使用前确认：

- [ ] 配置文件中 `export_geojson: true`
- [ ] 配置文件中 `enable_deduplication: true`（推荐）
- [ ] 配置文件中 `generate_map: true`
- [ ] 运行检测并等待完成
- [ ] 查看 `data/output/` 目录确认文件生成

### 11.3 输出文件用途

| 文件 | 给谁用 | 用途 |
|------|--------|------|
| `detections_unique.geojson` | GIS技术人员 | 导入GIS系统分析 |
| `map.html` | 项目管理人员 | 快速查看检测结果 |
| `summary.txt` | 所有人员 | 了解检测概况 |
| `detections_offline.csv` | 数据分析人员 | 详细数据分析 |
| `images/` | 审核人员 | 人工复核检测结果 |

---

**编写时间**: 2026-02-25  
**适用版本**: v2.1.0+  
**文档版本**: v1.0

如有问题，请查看：
- 技术实现文档：`GeoJSON输出和智能去重实现文档.md`
- 系统主文档：`README.md`
