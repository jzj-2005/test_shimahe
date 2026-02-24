# 无人机视频推理使用指南

## 📋 目录

- [快速开始](#快速开始)
- [环境要求](#环境要求)
- [处理流程](#处理流程)
- [验证与报告](#验证与报告)
- [常见问题](#常见问题)
- [技术架构](#技术架构)

---

## 🚀 快速开始

### 下午拿到视频后的完整流程

```bash
# 1. 激活环境
conda activate yolo11m-orthophoto

# 2. 将视频放入指定目录
# 复制视频到: d:\jzj\siluan_new\data\input\videos\

# 3. 运行视频推理
python run_offline.py "data/input/videos/DJI_XXXX.MP4"
# 等待处理完成（10-20分钟）

# 4. 导出GeoJSON
python tools/export_to_geojson.py data/output/csv/detections_offline.csv

# 5. 在地图上查看结果
python tools/quick_visualize.py

# 6. 抽样验证坐标准确度（可选）
python tools/sample_validation.py --samples 20

# 7. 生成提交报告
python tools/generate_report.py
```

**总耗时**: 30-40分钟（包括处理+验证）

---

## 💻 环境要求

### 硬件要求

- **GPU**: NVIDIA显卡（当前: RTX 3050 6GB） ✅
- **内存**: 建议16GB以上
- **存储**: 至少10GB可用空间

### 软件依赖

- **Python**: 3.8+ 
- **Conda环境**: `yolo11m-orthophoto` ✅
- **FFmpeg**: ⚠️ **需要安装**

#### 安装FFmpeg

**方法1: Chocolatey（推荐）**
```bash
choco install ffmpeg
```

**方法2: 手动下载**
1. 下载: https://ffmpeg.org/download.html
2. 解压到 `C:\ffmpeg`
3. 添加到PATH: `C:\ffmpeg\bin`

**验证安装**:
```bash
ffmpeg -version
```

### Python依赖

已安装在conda环境中：
- torch (CUDA 12.1)
- ultralytics (YOLOv11)
- opencv-python
- pandas
- loguru
- tqdm
- pyyaml

---

## 📹 处理流程

### 1. 输入数据要求

#### 视频文件

- **格式**: MP4, MOV, AVI等
- **编码**: H.264或H.265
- **分辨率**: 1080p或4K
- **来源**: DJI无人机录制

#### SRT字幕文件

**位置要求**（二选一）：
1. **嵌入视频中**: 自动提取（需要FFmpeg）
2. **同名文件**: 例如 `DJI_0001.MP4` + `DJI_0001.srt`

**SRT格式示例**:
```
1
00:00:00,000 --> 00:00:00,033
<font size="28">FrameCnt: 1, DiffTime: 33ms
2024-02-04 14:26:22.123
[latitude: 22.779953] [longitude: 114.100891] [altitude: 139.231]
[yaw: 45.2] [pitch: -90.0] [roll: 0.5]
</font>
```

**必需字段**:
- `latitude`: 纬度
- `longitude`: 经度
- `altitude`: 飞行高度（米）

**可选字段**:
- `yaw`, `pitch`, `roll`: 姿态角

### 2. 运行推理

```bash
# 基本用法
python run_offline.py "视频路径.MP4"

# 指定SRT文件（如果不是同名）
python run_offline.py "视频.MP4" --srt "字幕.srt"

# 跳帧处理（加快速度）
# 在 config/offline_config.yaml 中设置:
# video_processing:
#   frame_skip: 2  # 每2帧处理1帧
```

### 3. 处理进度监控

**终端输出示例**:
```
============================================================
无人机水利四乱巡检系统 - 离线处理模式
============================================================
视频文件: data/input/videos/DJI_0001.MP4
============================================================

步骤1: 提取SRT字幕
✓ SRT文件已找到: DJI_0001.srt

步骤2: 解析SRT数据  
✓ 解析945条位姿记录

步骤3: 打开视频文件
✓ 视频信息: 1920x1080, 30fps, 1800帧

步骤4: 开始逐帧处理
处理进度: 100%|████████████| 1800/1800 [15:23<00:00, 1.95it/s]

处理完成!
```

### 4. 输出文件

```
data/output/
├── csv/
│   └── detections_offline.csv          # 检测结果CSV
├── images/
│   ├── frame_0000_obj_001.jpg          # 检测目标截图
│   ├── frame_0000_obj_002.jpg
│   └── ...
├── detections.geojson                   # GeoJSON格式
├── detections_high_conf.geojson         # 高置信度检测
├── summary.txt                          # 统计摘要
├── map.html                             # 交互式地图
├── validation.html                      # 验证工具（可选）
├── delivery_report.md                   # 提交报告
└── offline_log.txt                      # 处理日志
```

---

## 🗺️ 验证与报告

### 步骤1: 导出GeoJSON

```bash
python tools/export_to_geojson.py data/output/csv/detections_offline.csv

# 可选参数:
# --min-confidence 0.5     # 只导出置信度>0.5的检测
# --classes Sheds Debris   # 只导出特定类别
```

**输出**:
- `detections.geojson` - 所有检测
- `detections_high_conf.geojson` - 高置信度检测
- `summary.txt` - 统计摘要

### 步骤2: 可视化查看

```bash
python tools/quick_visualize.py

# 或指定GeoJSON文件:
python tools/quick_visualize.py data/output/detections.geojson
```

**功能**:
- 🌐 在浏览器中打开交互式地图
- 🎨 不同类别显示不同颜色
- 🔍 点击检测框查看详细信息
- 📍 自动缩放到检测区域

### 步骤3: 抽样验证（可选）

```bash
python tools/sample_validation.py --samples 20
```

**操作**:
1. 系统随机抽取20个检测目标
2. 在地图上显示预测位置（蓝色标记）
3. 用户点击真实位置
4. 自动计算误差并进入下一个
5. 完成后导出验证结果JSON

**输出**: `validation_results_YYYY-MM-DD.json`

### 步骤4: 生成提交报告

```bash
python tools/generate_report.py

# 包含验证结果:
python tools/generate_report.py --validation validation_results_YYYY-MM-DD.json

# 包含视频信息:
python tools/generate_report.py --video-name "DJI_0001.MP4" --duration "10分钟" --frames 1800
```

**输出**: `delivery_report.md` - 完整的Markdown报告

---

## ❓ 常见问题

### Q1: FFmpeg未安装

**现象**: 提示"无法找到FFmpeg"

**解决**:
```bash
# 使用Chocolatey安装
choco install ffmpeg

# 或手动下载: https://ffmpeg.org/download.html
# 添加到PATH环境变量
```

### Q2: 找不到SRT文件

**现象**: 提示"无法获取SRT文件"

**解决**:
1. 检查视频同目录是否有同名`.srt`文件
2. 或手动指定: `python run_offline.py video.MP4 --srt subtitle.srt`
3. 确保SRT格式正确（包含GPS信息）

### Q3: GPU内存不足

**现象**: CUDA out of memory

**解决**:
```yaml
# 修改 config/yolo_config.yaml
detection:
  imgsz: 640  # 从1280降到640
```

或者增加跳帧:
```yaml
# 修改 config/offline_config.yaml
video_processing:
  frame_skip: 3  # 每3帧处理1帧
```

### Q4: 处理速度太慢

**现象**: 处理1分钟视频需要5分钟

**优化方案**:
1. 增加跳帧: `frame_skip: 2`
2. 降低输入尺寸: `imgsz: 640`
3. 关闭图像保存: `save_images: false`
4. 关闭实时显示: `realtime_display: false`

### Q5: CSV中类别显示为class_X

**现象**: CSV显示`class_9`而不是`Storage Zones`

**解决**: 确保 `config/yolo_config.yaml` 中类别映射完整（已修复）

### Q6: 坐标明显偏差

**现象**: 地图上检测框位置不对

**检查**:
1. SRT中GPS坐标是否正确
2. 飞行高度是否合理（100-200米）
3. 相机参数是否匹配（DJI 4TD）

---

## 🏗️ 技术架构

### 系统组件

```
视频推理系统
├── 输入层
│   ├── VideoFileReader      # 视频文件读取
│   ├── SRTExtractor         # SRT字幕提取
│   └── SRTParser            # GPS数据解析
│
├── 处理层
│   ├── DataSynchronizer     # 时间同步
│   ├── YOLODetector         # 目标检测
│   └── CoordinateTransformer # 坐标转换
│
└── 输出层
    ├── CSVWriter            # CSV结果写入
    ├── ImageSaver           # 目标截图保存
    └── Visualizer           # 实时可视化
```

### 坐标转换原理

```
像素坐标 → 地理坐标转换流程:

1. 计算地面分辨率 (GSD):
   GSD = (传感器尺寸 × 飞行高度) / (焦距 × 图像尺寸)
   
2. 像素偏移 → 地面距离:
   dx = (u - cx) × GSD_x  # 东向距离（米）
   dy = -(v - cy) × GSD_y # 北向距离（米）
   
3. 地面距离 → 经纬度偏移:
   Δlat = dy / 110540
   Δlon = dx / (111320 × cos(纬度))
   
4. 目标坐标 = 无人机坐标 + 偏移量
```

### 数据流图

```
视频帧 ──┐
         ├─> 时间同步 ─> YOLO检测 ─> 坐标转换 ─> CSV输出
SRT数据 ─┘                                    └─> 地图可视化
```

---

## 📊 配置文件说明

### offline_config.yaml

```yaml
video_processing:
  frame_skip: 1        # 跳帧：1=每帧处理，2=每2帧处理1次
  start_frame: 0       # 起始帧
  end_frame: 0         # 结束帧（0=处理到末尾）

data_sync:
  sync_method: "timestamp"
  timestamp_tolerance: 100  # 时间容差（毫秒）

output:
  csv_path: "./data/output/csv/detections_offline.csv"
  save_images: true    # 是否保存检测截图
  image_format: "full" # full=完整标注帧, crop=只保存目标
```

### yolo_config.yaml

```yaml
detection:
  confidence_threshold: 0.25  # 置信度阈值
  imgsz: 1280                 # 输入尺寸

model:
  device: "cuda"              # cuda或cpu

classes:
  target_classes: null        # null=检测所有类别
  names:                      # 11个类别映射
    0: "Water Bodies"
    1: "Vegetation"
    # ... 等等
```

### camera_params.yaml

```yaml
camera:
  model: "DJI_4TD"
  resolution:
    width: 5472
    height: 3648
  focal_length: 8.8  # mm

orthogonal_mode:
  assume_vertical: true         # 假设垂直拍摄
  use_attitude_correction: false # 不使用姿态修正
```

---

## 🎯 验证工具使用

### 工具1: export_to_geojson.py

**功能**: 将CSV转换为GeoJSON格式

```bash
# 基本用法
python tools/export_to_geojson.py data/output/csv/detections_offline.csv

# 高级用法
python tools/export_to_geojson.py \
    data/output/csv/detections_offline.csv \
    --min-confidence 0.5 \
    --classes Sheds Debris Storage\ Zones
```

**输出**: 
- `detections.geojson`
- `detections_high_conf.geojson`
- `summary.txt`

---

### 工具2: quick_visualize.py

**功能**: 在浏览器中查看检测结果

```bash
# 默认使用 data/output/detections.geojson
python tools/quick_visualize.py

# 指定文件
python tools/quick_visualize.py data/output/detections_high_conf.geojson

# 生成但不打开浏览器
python tools/quick_visualize.py --no-open
```

**功能特性**:
- 🎨 不同类别显示不同颜色
- 📍 点击查看检测详情
- 🔍 自动缩放到检测区域
- 📊 实时统计面板

---

### 工具3: sample_validation.py

**功能**: 交互式验证坐标准确度

```bash
# 验证20个样本
python tools/sample_validation.py --samples 20

# 验证正射图片结果
python tools/sample_validation.py \
    data/output/csv/detections_orthophoto.csv \
    --samples 10
```

**操作步骤**:
1. 浏览器打开验证界面
2. 点击"显示预测位置"按钮
3. 地图上出现蓝色标记（预测位置）
4. 在地图上点击目标的**真实位置**
5. 系统计算误差并自动进入下一个
6. 完成后点击"导出验证结果"

**输出**: `validation_results_YYYY-MM-DD.json`

---

### 工具4: generate_report.py

**功能**: 生成完整的Markdown报告

```bash
# 基本报告
python tools/generate_report.py

# 包含验证结果
python tools/generate_report.py \
    --validation validation_results_2026-02-11.json

# 包含视频信息
python tools/generate_report.py \
    --video-name "DJI_0001.MP4" \
    --duration "10分钟" \
    --frames 1800 \
    --validation validation_results_2026-02-11.json
```

**输出**: `delivery_report.md` - 完整的提交报告

---

## 📦 提交清单

### 必须提交

- ✅ `detections_offline.csv` - CSV检测结果
- ✅ `detections.geojson` - GeoJSON可视化数据
- ✅ `map.html` - 交互式地图
- ✅ `delivery_report.md` - 检测报告

### 可选提交

- ⭐ `validation_results.json` - 验证结果（如果完成）
- ⭐ `summary.txt` - 统计摘要
- ⭐ 检测目标截图（选择性提交部分）

---

## 🔧 故障排除

### 问题1: "target_classes: []" 导致无检测

**已修复**: 配置文件已改为 `target_classes: null`

### 问题2: 时间同步失败

**检查**:
- SRT文件格式是否正确
- 时间戳范围是否匹配
- 容差是否足够（100ms）

### 问题3: CSV写入权限错误

**已修复**: CSV写入器已改为持久化文件句柄

### 问题4: 可视化边框太细

**已修复**: 
- 边框粗细: 6像素
- 字体大小: 1.2
- 不同类别不同颜色

---

## 🎨 检测类别与颜色

| ID | 类别名称 | 英文名称 | 颜色 |
|----|---------|---------|------|
| 0 | 水体 | Water Bodies | 浅蓝色 |
| 1 | 植被 | Vegetation | 绿色 |
| 2 | 采矿区 | Mining Area | 蓝色 |
| 3 | 垃圾 | Debris | 橙色 |
| 4 | 工业建筑 | Industrial Buildings | 深紫 |
| 5 | 水务设施 | Waterway Facilities | 青色 |
| 6 | 水利控制 | Hydraulic Controls | 粉色 |
| 7 | 住宅 | Residences | 黄色 |
| 8 | 棚子 | Sheds | 黄色 |
| 9 | 堆放区 | Storage Zones | 紫色 |
| 10 | 娱乐区 | Recreation Areas | 粉红 |

---

## 📈 性能优化建议

### 处理速度优化

| 配置 | 速度 | 精度 | 推荐场景 |
|-----|------|------|---------|
| `imgsz: 1280, skip: 1` | 慢 | 高 | 初版提交 |
| `imgsz: 1280, skip: 2` | 中 | 高 | 快速验证 |
| `imgsz: 640, skip: 2` | 快 | 中 | 实时演示 |

### GPU使用率

- 当前配置: RTX 3050 6GB
- 建议设置: `imgsz: 1280`, `batch_size: 1`
- 如果OOM: 降低到 `imgsz: 640`

---

## 🚀 下一步：实时视频流

### 离线 → 实时的改造

| 组件 | 离线模式 | 实时模式 |
|-----|---------|---------|
| 输入 | MP4文件 | RTSP视频流 |
| 位姿 | SRT文件 | MQTT订阅 |
| 输出 | CSV文件 | MQTT发布 |
| 核心算法 | **完全相同** | **完全相同** |

**代码复用率**: 约90%

主要修改:
- `VideoFileReader` → `RTSPReader` (已有代码)
- `SRTParser` → `MQTTSubscriber` (已有代码)
- `CSVWriter` → `MQTTPublisher` (已有代码)

---

## 📞 技术支持

### 项目结构

```
d:\jzj\siluan_new\
├── run_offline.py              # 视频推理入口
├── config/                     # 配置文件
│   ├── offline_config.yaml
│   ├── yolo_config.yaml
│   └── camera_params.yaml
├── src/                        # 核心代码
│   ├── offline_pipeline.py
│   ├── input/                  # 输入模块
│   ├── detection/              # 检测模块
│   ├── transform/              # 坐标转换
│   └── output/                 # 输出模块
├── tools/                      # 验证工具
│   ├── export_to_geojson.py
│   ├── quick_visualize.py
│   ├── sample_validation.py
│   └── generate_report.py
└── data/
    ├── input/videos/           # 放视频到这里
    └── output/                 # 结果输出
```

### 关键文件

- **入口**: `run_offline.py`
- **配置**: `config/*.yaml`
- **核心流程**: `src/offline_pipeline.py`
- **检测器**: `src/detection/yolo_detector.py`
- **坐标转换**: `src/transform/coord_transform.py`

---

## ✅ 验收标准

### 处理成功

- ✅ CSV文件生成
- ✅ 检测数量>0
- ✅ 所有坐标非零且在合理范围内
- ✅ 无严重错误日志

### 坐标可用

- ✅ 目视验证：检测框在合理位置
- ✅ 抽样验证：平均误差<5米
- ✅ 无系统性偏差（不是全部向一个方向偏）

### 可提交

- ✅ 完整的CSV结果
- ✅ GeoJSON可视化文件
- ✅ 交互式HTML地图
- ✅ 验证报告（含误差统计）
- ✅ 使用文档

---

**最后更新**: 2026-02-11

**版本**: v1.0 - 初版交付
