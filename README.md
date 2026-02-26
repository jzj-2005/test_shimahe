# 无人机水利四乱巡检系统

基于YOLOv11x深度学习的无人机目标检测系统，自动计算检测目标的GPS地理坐标。支持离线视频处理和实时流处理两种模式。

## 目录

- [项目概述](#项目概述)
- [快速开始](#快速开始)
- [目录结构](#目录结构)
- [工作模式详解](#工作模式详解)
- [配置文件详解](#配置文件详解)
- [输出文件说明](#输出文件说明)
- [验证流程](#验证流程)
- [故障排查](#故障排查)
- [项目交接清单](#项目交接清单)

---

## 项目概述

### 核心功能

- ✅ **离线视频处理**：处理本地DJI视频文件+SRT字幕，快速验证算法
- ✅ **实时流处理**：接收RTSP视频流+MQTT位姿数据，实时检测和输出
- ✅ **OCR飞行数据提取**：支持从视频画面OSD识别GPS、高度等信息（无需SRT字幕）
- ✅ **YOLOv11x检测**：高精度目标检测，支持多类别识别
- ✅ **坐标转换**：像素坐标→CGCS2000地理坐标（符合国家标准GB/T 18522-2020）
- ✅ **增强版坐标转换**（v2.0新增）：支持完整3D姿态修正和GPS质量控制，精度提升60-70%
- ✅ **CSV报告输出**：结构化数据导出，包含四角点地理坐标和GPS质量信息
- ✅ **智能去重**（v2.1新增）：自动去除重复检测，保留最佳质量目标，数据量减少70-97%
- ✅ **GeoJSON自动导出**（v2.1新增）：检测完成后自动生成GIS矢量数据，支持QGIS/ArcGIS
- ✅ **可视化地图自动生成**（v2.1新增）：自动生成交互式HTML地图，可浏览器查看
- ✅ **检测截图保存**：自动保存检测目标图像
- ✅ **实时可视化**：显示检测框、GPS信息、处理速度等

### 两种工作模式对比

| 特性 | 视频处理模式 | 实时流处理模式 |
|------|-------------|---------------|
| **适用场景** | 算法验证、效果测试 | 实际巡检作业 |
| **数据源** | 本地视频文件(.MP4) + SRT字幕/OCR | RTSP视频流 + MQTT位姿/OCR备用 |
| **时间同步** | 精确(<100ms) | 实时同步 |
| **处理速度** | 可跳帧加速 | 必须实时处理 |
| **优势** | 可重复测试、结果稳定 | 即时反馈、无需存储 |
| **启动命令** | `run_video.bat` | `run_realtime.py` |

### 系统架构

```
[视频源] → [数据同步] → [YOLO检测] → [坐标转换] → [结果输出]
   ↓           ↓            ↓             ↓            ↓
  MP4/RTSP   SRT/MQTT    YOLOv11x    像素→GPS      CSV/图片
```

### 技术栈

- Python 3.8+
- PyTorch (CUDA 11.8+)
- Ultralytics YOLOv11x
- PaddleOCR (视频OSD文字识别)
- FFmpeg (SRT提取)
- OpenCV (视频处理)
- Paho-MQTT (实时通信)

### 📚 相关文档

**v2.1新增文档**：

- 📘 **[GeoJSON输出和智能去重实现文档.md](GeoJSON输出和智能去重实现文档.md)** - 技术实现细节、算法原理、性能分析
- 📗 **[GeoJSON和地图输出使用指南.md](GeoJSON和地图输出使用指南.md)** - 操作手册、配置指南、常见问题

**v2.0文档**：

- 📙 **[增强版坐标转换实现方案.md](增强版坐标转换实现方案.md)** - 3D姿态修正技术方案
- 📕 **[增强版转换器使用指南.md](增强版转换器使用指南.md)** - 坐标转换配置指南

---

## 快速开始

### 1. 环境准备

**前置条件清单：**

- [ ] Windows 10/11 或 Linux
- [ ] Python 3.8+ 已安装
- [ ] （推荐）NVIDIA GPU + CUDA 11.8+
- [ ] 网络连接（下载依赖和模型）

### 2. 一键安装

```bash
# 1. 进入项目目录
cd d:\jzj\siluan_new

# 2. 创建conda环境
conda create -n drone_inspection python=3.9 -y
conda activate drone_inspection

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装FFmpeg（Windows）
choco install ffmpeg -y
# 或手动下载: https://ffmpeg.org/download.html

# 5. 验证安装
python -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')"
ffmpeg -version
```

### 3. 准备模型

下载训练好的YOLOv11x模型：

```bash
# 将模型文件放入 models/ 目录
models/
└── yolov11x.pt  # 确保此文件存在
```

### 4. 第一次运行（视频处理示例）

```bash
# 方法1: 使用批处理脚本（Windows推荐）
run_video.bat "data\input\videos\测试视频.MP4"

# 方法2: 使用Python脚本
python run_offline.py "data/input/videos/测试视频.MP4"

# 运行后查看输出
data/output/csv/detections_offline.csv       # CSV结果
data/output/images/offline/                   # 检测截图
```

### 5. 查看结果 ⭐ v2.1自动输出

**检测完成后自动生成所有输出文件！**

```bash
# 方式1：查看可视化地图（推荐）
start data/output/map.html
# 或在配置中设置 auto_open_map: true 自动打开

# 方式2：查看统计摘要
notepad data/output/summary.txt

# 方式3：在GIS软件中查看
# QGIS: 图层 → 添加矢量图层 → data/output/geojson/detections_unique.geojson

# 方式4：查看CSV原始数据
# Excel打开: data/output/csv/detections_offline.csv
```

**输出文件清单**：

- ✅ `csv/detections_offline.csv` - CSV原始数据
- ✅ `geojson/detections_unique.geojson` - GIS矢量数据（已去重）
- ✅ `map.html` - 交互式地图
- ✅ `summary.txt` - 统计摘要
- ✅ `images/` - 检测截图

**传统验证流程**（可选）：

```bash
# 如果需要手动生成或自定义参数
run_validation.bat
```

---

## 目录结构

```
siluan_new/                           # 项目根目录
│
├── 📁 config/                        # ⭐ 所有配置文件
│   ├── camera_params.yaml           # [重要] 相机参数（影响坐标准确性）
│   ├── yolo_config.yaml             # YOLO检测配置（置信度、类别等）
│   ├── offline_config.yaml          # 视频处理配置（跳帧、输出设置）
│   └── realtime_config.yaml         # 实时流配置（RTSP、MQTT连接）
│
├── 📁 src/                          # ⭐ 核心源代码
│   │
│   ├── 📁 input/                    # 数据输入层
│   │   ├── video_file_reader.py    # [视频] 读取本地MP4文件
│   │   ├── srt_extractor.py        # [视频] 从视频提取SRT字幕
│   │   ├── srt_parser.py           # [视频] 解析SRT获取GPS数据
│   │   ├── osd_ocr_reader.py       # [新增] OCR识别视频OSD信息
│   │   ├── rtsp_stream_reader.py   # [实时] 读取RTSP视频流
│   │   └── mqtt_client.py          # [实时] 接收MQTT位姿数据
│   │
│   ├── 📁 detection/                # 检测层
│   │   └── yolo_detector.py        # YOLOv11x目标检测封装
│   │
│   ├── 📁 transform/                # 坐标转换层（核心算法）
│   │   ├── camera_model.py         # 相机参数模型（GSD计算）
│   │   ├── coord_transform.py      # 像素坐标→GPS坐标转换（简化版）
│   │   └── coord_transform_new.py  # [v2.0新增] 增强版转换器（3D姿态修正）
│   │
│   ├── 📁 output/                   # 输出层
│   │   ├── csv_writer.py           # CSV报告生成
│   │   ├── image_saver.py          # 检测截图保存
│   │   └── report_generator.py     # 汇总报告生成
│   │
│   ├── 📁 utils/                    # 工具模块
│   │   ├── data_sync.py            # 时间戳同步（帧↔位姿匹配）
│   │   ├── visualizer.py           # 实时可视化显示
│   │   ├── logger.py               # 日志系统
│   │   └── config_loader.py        # 配置文件加载
│   │
│   ├── offline_pipeline.py          # ⭐ [入口] 视频处理完整流程
│   ├── realtime_pipeline.py         # ⭐ [入口] 实时流处理完整流程
│   └── main.py                      # 主程序入口（命令行接口）
│
├── 📁 tools/                        # ⭐ 验证和辅助工具
│   ├── export_to_geojson.py        # 导出GeoJSON格式（用于GIS软件）
│   ├── quick_visualize.py          # 生成交互式地图（Leaflet）
│   ├── sample_validation.py        # 坐标准确度验证工具
│   └── generate_report.py          # 生成Markdown提交报告
│
├── 📁 models/                       # ⭐ 模型文件
│   └── yolov11x.pt                 # YOLOv11x权重文件（必需）
│
├── 📁 data/                         # 数据目录
│   ├── input/videos/               # 输入视频存放处
│   ├── temp/srt/                   # 临时SRT文件
│   └── output/                     # ⭐ 所有输出结果
│       ├── csv/                    # CSV检测报告
│       │   ├── detections_offline.csv
│       │   └── detections_realtime.csv
│       ├── images/                 # 检测截图
│       │   ├── offline/
│       │   └── realtime/
│       ├── geojson/                # v2.1新增：GIS矢量数据
│       │   ├── detections_raw.geojson      # 原始完整数据
│       │   ├── detections_unique.geojson   # 智能去重数据（推荐）
│       │   └── detections_high_conf.geojson # 高置信度数据
│       ├── map.html                # v2.1新增：可视化地图
│       └── summary.txt             # v2.1新增：统计摘要
│
├── 📁 docs/                         # 文档
│   └── DJI_MQTT_SETUP.md           # DJI无人机MQTT配置指南
│
├── 📁 tests/                        # 测试文件
│   └── test_coord_transform_new.py # 增强版转换器单元测试
│
├── 📄 run_offline.py                # ⭐ [快捷启动] 视频处理
├── 📄 run_realtime.py               # ⭐ [快捷启动] 实时流处理
├── 📄 run_video.bat                 # ⭐ [Windows批处理] 视频处理
├── 📄 run_validation.bat            # ⭐ [Windows批处理] 完整验证流程
│
├── 📄 requirements.txt              # Python依赖列表
├── 📄 README.md                     # ⭐ 项目主文档（本文件）
├── 📄 README_VIDEO.md               # 视频处理详细文档
├── 📄 QUICKSTART.md                 # 快速开始指南
├── 📄 增强版坐标转换实现方案.md      # [v2.0新增] 增强版转换器技术方案
├── 📄 增强版转换器使用指南.md        # [v2.0新增] 增强版转换器使用手册
├── 📄 GeoJSON输出和智能去重实现文档.md  # [v2.1新增] 后处理功能技术文档
└── 📄 GeoJSON和地图输出使用指南.md    # [v2.1新增] GIS输出操作手册
```

**目录说明：**

- ⭐ 标记的是最重要的文件/目录
- [视频] 标记的仅用于视频处理模式
- [实时] 标记的仅用于实时流模式
- [重要] 标记的配置需要根据实际情况调整

---

## 工作模式详解

### 模式1：视频处理（推荐用于测试验证）

#### 1.1 适用场景

- ✅ 算法效果验证
- ✅ 坐标准确性测试
- ✅ 参数调优
- ✅ 生成演示材料

#### 1.2 数据准备

```
准备文件：
data/input/videos/
└── DJI_0001.MP4              # DJI无人机录制的视频
    └── DJI_0001.SRT          # （可选）如果有同名SRT文件会自动使用

注意：
- 如果视频没有SRT字幕文件，系统会自动尝试从视频中提取
- 如果视频不包含字幕轨道，系统会自动启用OCR模式从画面识别飞行数据
```

#### 1.3 启动方法

**方法A：批处理脚本（Windows推荐）**

```bash
run_video.bat "视频路径.MP4"
```

**方法B：Python脚本**

```bash
python run_offline.py "data/input/videos/DJI_0001.MP4"
```

**方法C：完整命令（更多参数）**

```bash
python -m src.main \
  --mode offline \
  --video "data/input/videos/DJI_0001.MP4" \
  --config config/offline_config.yaml
```

#### 1.4 处理流程

```
1. [SRT提取] 自动从视频提取SRT字幕（使用FFmpeg）
   ↓
2. [数据解析] 解析SRT文件，提取每帧的GPS、高度、姿态数据
   ↓
3. [视频解码] 逐帧读取视频
   ↓
4. [时间同步] 将视频帧与位姿数据精确匹配（<100ms误差）
   ↓
5. [目标检测] YOLO检测画面中的目标（违建、垃圾等）
   ↓
6. [坐标转换] 将检测框像素坐标转换为CGCS2000地理坐标（WGS84→CGCS2000）
   ↓
7. [结果输出] 生成CSV报告 + 保存检测截图
```

#### 1.5 配置调整

编辑 [`config/offline_config.yaml`](config/offline_config.yaml)：

```yaml
# 性能优化
input:
  frame_skip: 2              # 跳帧处理（2=每2帧处理1帧，加快速度）
  start_frame: 0             # 从第几帧开始
  end_frame: 0               # 到第几帧结束（0=处理到最后）

# 时间同步
data_sync:
  timestamp_tolerance: 100   # 时间容差(ms)，SRT同步精度高可设置100

# 输出控制
output:
  save_images: true          # 是否保存检测截图
  image_format: "full"       # full=全帧标注图，crop=仅目标区域
  csv_write_mode: "overwrite" # overwrite=覆盖，append=追加

# 可视化
visualization:
  realtime_display: true     # 是否实时显示处理画面
  display_width: 1280        # 显示窗口宽度
```

#### 1.6 输出结果

```
data/output/
├── csv/
│   └── detections_offline.csv                    # ⭐ CSV检测报告（原始数据）
├── images/offline/
│   ├── frame_000001_obj_001_Vegetation_20260210_103015.jpg
│   ├── frame_000002_obj_001_Sheds_20260210_103016.jpg
│   └── ...                                       # 所有检测截图
├── geojson/                                      # ⭐ v2.1新增：GIS数据
│   ├── detections_raw.geojson                    # 原始完整数据
│   ├── detections_unique.geojson                 # 智能去重数据（推荐）
│   └── detections_high_conf.geojson              # 高置信度数据
├── map.html                                      # ⭐ v2.1新增：可视化地图
├── summary.txt                                   # ⭐ v2.1新增：统计摘要
└── offline_log.txt                               # 处理日志
```

### 模式2：实时流处理（实际巡检场景）

#### 2.1 适用场景

- ✅ 实际巡检作业
- ✅ 实时目标反馈
- ✅ 无需存储大量视频

#### 2.2 前置配置

**步骤1：配置DJI无人机**
参考 [`docs/DJI_MQTT_SETUP.md`](docs/DJI_MQTT_SETUP.md) 完成：

1. 开启DJI Pilot 2的MQTT推送
2. 配置RTSP视频流
3. 获取无人机SN号

**步骤2：编辑实时配置**
编辑 [`config/realtime_config.yaml`](config/realtime_config.yaml)：

```yaml
# RTSP视频流配置
rtsp:
  url: "rtsp://192.168.1.100:8554/live"  # 修改为实际RTSP地址
  reconnect_interval: 5                   # 断线重连间隔(秒)
  buffer_size: 1                          # 缓冲区大小

# MQTT位姿数据配置
mqtt:
  broker: "mqtt.dji.com"                  # MQTT服务器地址
  port: 1883
  username: "your_username"               # 修改为实际用户名
  password: "your_password"               # 修改为实际密码
  client_id: "drone_inspection_001"
  topics:
    aircraft_state: "thing/product/{gateway_sn}/state"  # {gateway_sn}替换为实际SN

# 数据同步
data_sync:
  max_time_diff: 200                      # 最大时间差(ms)
  sync_strategy: "nearest"                # 同步策略
```

#### 2.3 启动方法

```bash
# 激活环境
conda activate drone_inspection

# 启动实时处理
python run_realtime.py

# 或使用完整命令
python -m src.main --mode realtime --config config/realtime_config.yaml
```

#### 2.4 运行状态

启动后会看到：

```
[INFO] 连接RTSP流: rtsp://192.168.1.100:8554/live
[INFO] 连接MQTT: mqtt.dji.com:1883
[INFO] 等待位姿数据...
[INFO] 开始实时处理 [帧率: 25fps, 延迟: 120ms]
[INFO] 检测到目标: Vegetation, 置信度: 0.85, GPS: (22.779814, 114.101319)
```

#### 2.5 实时输出

```
data/output/
├── csv/
│   └── detections_realtime.csv                   # 实时追加检测结果（原始数据）
├── images/realtime/
│   └── detection_20260210_103015_001.jpg        # 实时保存截图
├── geojson/                                      # v2.1可选：结束后生成
│   ├── detections_raw.geojson                    # 原始完整数据
│   ├── detections_unique.geojson                 # 智能去重数据
│   └── detections_high_conf.geojson              # 高置信度数据
├── map.html                                      # v2.1可选：可视化地图
├── summary.txt                                   # v2.1可选：统计摘要
└── realtime_log.txt                              # 实时日志

注意：实时模式的GeoJSON和地图默认关闭（数据量大），可在配置中开启
```

#### 2.6 停止处理

按 `Ctrl+C` 或 `Esc` 键安全退出。

---

## OCR飞行数据提取功能

### 功能概述

系统支持使用OCR（光学字符识别）从视频画面的OSD（屏幕显示）区域提取飞行数据，作为SRT字幕的替代方案。

**使用场景：**
- ✅ 视频文件不包含SRT字幕轨道
- ✅ 无法从视频中提取字幕数据
- ✅ 实时模式下MQTT数据不可用时的备用方案

### 数据提取流程

```
视频帧 → 裁剪OSD区域 → PaddleOCR识别 → 文本解析 → 提取GPS/高度/姿态
```

### OCR配置

**离线模式配置** (`config/offline_config.yaml`):

```yaml
ocr:
  enabled: true              # 是否启用OCR
  engine: "paddleocr"        # OCR引擎
  language: "ch"             # 语言：ch(中文) / en(英文)
  
  roi:                       # 感兴趣区域（OSD位置）
    x: 0
    y: 0
    width: 800               # ⚠️ 需足够宽以捕获完整数据（含小数）
    height: 300
  
  frame_interval: 5          # 每N帧识别一次
  use_gpu: false             # 是否使用GPU加速
```

**实时模式配置** (`config/realtime_config.yaml`):

```yaml
ocr_fallback:
  enabled: true              # 启用OCR备用
  frame_interval: 10         # 实时模式建议更大间隔
  # 其他参数同上
```

### 性能对比

| 指标 | SRT模式 | OCR模式 |
|------|---------|---------|
| **准确度** | ★★★★★ | ★★★★☆ |
| **速度** | ★★★★★ | ★★★☆☆ |
| **GPU占用** | 低 | 中 |
| **适用场景** | 优先推荐 | 备用方案 |

### 使用示例

```bash
# 离线模式自动检测：有SRT用SRT，无SRT用OCR
python run_offline.py "data/input/videos/video_no_srt.mp4"

# 查看日志确认使用的模式
# 输出：SRT不可用，切换到OCR模式提取飞行数据
```

### ROI区域调整

如果OCR识别效果不佳，可能需要调整ROI区域：

**⚠️ 重要：ROI宽度影响精度**

| ROI宽度 | 识别效果 |
|---------|----------|
| 600像素 | ❌ 高度只有整数（如139） |
| 800像素 | ✅ 完整精度（如139.365m） |

**调整步骤：**

1. 播放视频，确认OSD文字位置（通常在左上角）
2. 修改配置文件中的ROI参数：
   ```yaml
   roi:
     x: 0          # 左边距（像素）
     y: 0          # 上边距（像素）
     width: 800    # ⚠️ 推荐800以捕获完整数据
     height: 300   # 区域高度（300通常足够）
   ```
3. 重新运行测试

### 故障排查

**问题1：OCR未识别到任何文字**
- 检查ROI区域是否覆盖OSD文字
- 确认视频分辨率与ROI配置匹配
- 检查PaddleOCR是否正确安装

**问题2：GPS坐标或高度精度不足**
- **症状**：高度只有整数（如139），缺少小数部分（139.365）
- **原因**：ROI区域太小，裁剪掉了数据的小数部分
- **解决**：将ROI宽度从600增加到800像素
- 查看日志中的OCR识别原始文本确认
- 检查OSD格式是否为标准格式
- 必要时调整`_parse_osd_text`中的正则表达式

**问题3：OCR速度太慢**
- 增大`frame_interval`参数（如改为10）
- 缩小ROI区域尺寸
- 启用GPU加速：`use_gpu: true`

### 首次运行说明

PaddleOCR首次运行时会自动下载模型文件（约10MB），请确保网络连接正常。模型文件会缓存在本地，后续运行无需重复下载。

---

## 增强版坐标转换器（v2.0新增）⭐

### 功能概述

增强版坐标转换器是v2.0版本新增的核心功能，实现了完整的3D姿态修正和GPS质量控制，将检测目标定位精度从**5-10米提升到2-3米**，改善幅度达到**60-70%**。

**核心改进**：

1. ✅ **完整3D姿态修正** - 支持任意pitch/yaw/roll姿态下的精确转换
2. ✅ **GPS质量控制** - 自动识别和过滤低质量GPS数据
3. ✅ **RTK高精度识别** - 自动识别RTK厘米级定位（0.02-0.05米精度）
4. ✅ **误差估算** - 为每个检测结果提供预估误差范围
5. ✅ **质量标记** - 在CSV中添加GPS质量等级和定位状态

### 精度对比

| 场景 | 简化版误差 | 增强版误差 | 改善幅度 |
|------|----------|----------|---------|
| 垂直拍摄 (pitch≈-90°) | 3-5米 | 2-3米 | +30% |
| 轻微倾斜 (pitch≈-85°) | 8-10米 | **2-3米** | **+70%** |
| 明显倾斜 (pitch≈-80°) | 15-20米 | 3-5米 | **+75%** |
| 机身倾斜 (roll=5°) | 8-10米 | **2-3米** | **+70%** |
| RTK定位 | 3-5米 | **0.5-1米** | **+80%** |

### 快速启用

**步骤1**：编辑 `config/camera_params.yaml`

```yaml
coordinate_transform:
  use_enhanced: true  # 改为 true 启用增强版
```

**步骤2**：正常运行检测

```bash
python run_realtime.py  # 或 run_offline.py
```

系统会自动：
- ✅ 使用3D姿态修正算法
- ✅ 评估GPS质量并过滤低质量数据
- ✅ 在CSV中添加质量信息列

### OSD数据要求

为了充分利用增强版功能，MQTT OSD消息需要包含完整的姿态数据：

**必需字段**：
```json
{
  "timestamp": 1707730815123,
  "data": {
    "latitude": 22.779954,      // GPS纬度
    "longitude": 114.100891,    // GPS经度
    "altitude": 139.231,        // 飞行高度
    "pitch": -88.5,             // 俯仰角（关键）
    "yaw": 45.2,                // 偏航角（关键）
    "roll": 0.1                 // 横滚角（关键）
  }
}
```

**推荐字段**（质量控制）：
```json
{
  "data": {
    "gps_level": 5,                    // GPS信号强度
    "satellite_count": 18,             // 卫星数量
    "positioning_state": "RTK_FIXED"   // 定位状态（识别RTK）
  }
}
```

### CSV新增字段

增强版转换器会在CSV输出中添加以下质量信息列：

| 列名 | 说明 | 示例值 |
|------|------|--------|
| `gps_quality` | GPS质量等级 | RTK / HIGH / MEDIUM / LOW |
| `positioning_state` | 定位状态 | RTK_FIXED / GPS / DGPS |
| `estimated_error` | 预估误差（米） | 0.05 / 2.5 / 5.0 |
| `gps_level` | GPS信号强度 | 0-5 |
| `satellite_count` | 卫星数量 | 18 / 12 / 8 |

**质量等级说明**：

- **RTK**: RTK固定解，厘米级精度（0.02-0.05米）
- **HIGH**: 高质量GPS/RTK浮点解（0.5-3米）
- **MEDIUM**: 合格质量GPS（3-5米）
- **LOW**: 较差质量GPS（5-8米）
- **INVALID**: 信号太差，已自动过滤

### 详细文档

- 📄 **技术方案**：`增强版坐标转换实现方案.md` - 完整技术实现细节
- 📄 **使用指南**：`增强版转换器使用指南.md` - 配置和使用说明
- 📄 **单元测试**：`tests/test_coord_transform_new.py` - 测试和验证

### 向后兼容

- 增强版与简化版可通过配置文件灵活切换
- CSV格式完全兼容（新增列在末尾）
- 默认使用简化版，需手动开启增强版

---

## 配置文件详解

### camera_params.yaml（影响坐标准确性⭐）

**路径**：[`config/camera_params.yaml`](config/camera_params.yaml)

**关键参数**：

```yaml
camera:
  model: "M4TD"                          # 相机型号（Matrice 4T/4TD）
  
  resolution:                            # 图像分辨率
    width: 5472                          # [关键] 必须与实际拍摄分辨率一致
    height: 3648
  
  sensor_size:                           # 传感器物理尺寸（单位：mm）
    width: 13.2                          # [关键] 1/1.3英寸传感器宽度
    height: 8.8                          # [关键] 1/1.3英寸传感器高度
  
  focal_length: 8.8                      # [关键] 焦距（单位：mm）
  
  principal_point:                       # 主点坐标（图像中心）
    cx: 2736                             # width / 2
    cy: 1824                             # height / 2

earth:                                   # 地球参数（用于坐标转换）
  meters_per_degree_lat: 110540          # 每度纬度对应的米数
  meters_per_degree_lon: 111320          # 每度经度对应的米数（赤道处）

# v2.0新增：坐标转换器选择
coordinate_transform:
  use_enhanced: false                    # true=增强版，false=简化版
  
  quality_control:                       # GPS质量控制（仅增强版）
    enabled: true
    min_gps_level: 3                     # 最低GPS信号（1-5）
    min_satellite_count: 10              # 最少卫星数
    skip_on_low_quality: true            # 是否跳过低质量数据
```

**⚠️ 重要提示**：

- 这些参数直接影响GPS坐标计算精度
- 如果坐标偏差>100米，首先检查这里的参数
- 需要根据无人机实际相机参数调整

**如何获取准确参数**：

1. 查看无人机官方规格书
2. 查看照片EXIF信息：`exiftool 照片.jpg`
3. 如果无法获取，使用已知地标反推（后续可提供标定工具）

### yolo_config.yaml（影响检测效果）

**路径**：[`config/yolo_config.yaml`](config/yolo_config.yaml)

**关键参数**：

```yaml
model:
  path: "./models/yolov11x.pt"           # 模型文件路径
  device: "cuda"                         # cuda=GPU, cpu=CPU
  half_precision: false                  # 半精度加速（需要GPU）

detection:
  confidence_threshold: 0.25             # 置信度阈值（越低检出越多）
  iou_threshold: 0.45                    # NMS阈值
  imgsz: 1280                            # 推理图像尺寸（越大越慢但精度高）
  target_classes: null                   # 目标类别过滤（null=所有类别）

classes:                                 # 类别名称映射
  names:
    0: "Buildings"
    1: "Vegetation"
    2: "Cars"
    3: "Roads"
    4: "Waterways"
    5: "Farmland"
    6: "Bareground"
    7: "Landfills"
    8: "Sheds"
    9: "Storage Zones"
    10: "Illegal Structures"
```

**调优建议**：

- **提高检出率**：降低 `confidence_threshold` 到 0.2
- **减少误报**：提高 `confidence_threshold` 到 0.5
- **提高速度**：降低 `imgsz` 到 640
- **提高精度**：提高 `imgsz` 到 1920（需要更多显存）

### offline_config.yaml（视频处理参数）

**关键参数说明**：

```yaml
# 性能相关
frame_skip: 2                # 跳帧数（1=处理每帧，2=每2帧处理1次）
                             # 建议：测试时用1，实际处理用2-5

# 输出相关
save_images: true            # 是否保存截图（影响磁盘空间）
image_format: "full"         # full=全帧标注，crop=仅目标区域
                             # crop可节省磁盘空间

# 可视化
realtime_display: true       # 是否实时显示处理画面
                             # 关闭可提高处理速度10-20%
```

### realtime_config.yaml（实时流配置）

**关键参数说明**：

```yaml
# RTSP相关
rtsp:
  url: "rtsp://..."          # [必改] RTSP流地址
  reconnect_interval: 5      # 断线重连间隔
  timeout: 10                # 连接超时时间

# MQTT相关
mqtt:
  broker: "mqtt.dji.com"     # [必改] MQTT服务器
  username: "..."            # [必改] 用户名
  password: "..."            # [必改] 密码
  topics:
    aircraft_state: "..."    # [必改] 替换{gateway_sn}

# 性能相关
processing:
  frame_interval: 1          # 处理间隔（1=处理每帧）
  max_queue_size: 30         # 队列大小（防止延迟累积）
```

---

## 输出文件说明

### CSV检测报告（主要输出）

**文件路径**：

- 视频模式：`data/output/csv/detections_offline.csv`
- 实时模式：`data/output/csv/detections_realtime.csv`

**字段说明**：

| 列名 | 类型 | 说明 | 示例值 |
|------|------|------|--------|
| timestamp | 浮点数 | 时间戳(ms) | 1770186401669.089 |
| frame_number | 整数 | 视频帧号 | 123 |
| datetime | 字符串 | 日期时间 | 2026-02-10 10:30:15.123 |
| class_id | 整数 | 类别ID | 1 |
| class_name | 字符串 | 类别名称 | "Vegetation" |
| confidence | 浮点数 | 置信度 | 0.8327 |
| **corner1_lat** | 浮点数 | 矩形框角点1纬度 | 22.779961 |
| **corner1_lon** | 浮点数 | 矩形框角点1经度 | 114.101265 |
| **corner2_lat** | 浮点数 | 矩形框角点2纬度 | 22.779961 |
| **corner2_lon** | 浮点数 | 矩形框角点2经度 | 114.101373 |
| **corner3_lat** | 浮点数 | 矩形框角点3纬度 | 22.779668 |
| **corner3_lon** | 浮点数 | 矩形框角点3经度 | 114.101373 |
| **corner4_lat** | 浮点数 | 矩形框角点4纬度 | 22.779668 |
| **corner4_lon** | 浮点数 | 矩形框角点4经度 | 114.101265 |
| **center_lat** | 浮点数 | 目标中心纬度 | 22.779814 |
| **center_lon** | 浮点数 | 目标中心经度 | 114.101319 |
| altitude | 浮点数 | 飞行高度(m) | 139.231 |
| drone_lat | 浮点数 | 无人机纬度 | 22.779954 |
| drone_lon | 浮点数 | 无人机经度 | 114.100891 |
| image_path | 字符串 | 截图路径 | ./data/output/images/... |
| **gps_quality** | 字符串 | GPS质量等级（v2.0新增） | RTK / HIGH / MEDIUM |
| **positioning_state** | 字符串 | 定位状态（v2.0新增） | RTK_FIXED / GPS |
| **estimated_error** | 浮点数 | 预估误差米（v2.0新增） | 0.05 / 2.5 / 5.0 |
| **gps_level** | 整数 | GPS信号强度（v2.0新增） | 0-5 |
| **satellite_count** | 整数 | 卫星数量（v2.0新增） | 18 / 12 / 8 |

**注意事项**：

- 四个corner坐标定义了检测框的矩形范围
- center坐标是四个角点的平均值
- **所有坐标均为CGCS2000坐标系**（中国国家标准，EPSG:4490）
- 无人机GPS原始坐标为WGS84，已自动转换为CGCS2000
- 转换精度：简化版3-5米，增强版2-3米（v2.0）
- **v2.0新增**：后5列为GPS质量信息（仅增强版有值）

### GeoJSON文件（用于GIS软件）⭐ v2.1自动输出

**自动生成**（v2.1新增）：

运行检测后**自动生成**，无需手动执行脚本！

**输出文件**：

- `data/output/geojson/detections_raw.geojson` - 原始完整数据（所有帧的所有检测）
- `data/output/geojson/detections_unique.geojson` - **智能去重数据（推荐用于GIS）**
- `data/output/geojson/detections_high_conf.geojson` - 高置信度检测（>0.7）

**手动生成**（兼容旧方式）：

```bash
python tools/export_to_geojson.py data/output/csv/detections_offline.csv
```

**GIS软件使用**：

- **QGIS**: 图层 → 添加图层 → 矢量图层 → 选择 `detections_unique.geojson`
- **ArcGIS**: Add Data → 选择 `.geojson` 文件
- **Google Earth Pro**: 需先转换为KML格式
- **在线地图**: Leaflet.js、OpenLayers、Mapbox等

**坐标系说明**：

- 坐标系：CGCS2000 (EPSG:4490)
- 几何类型：Polygon（检测框四角点多边形）
- 属性：类别、置信度、GPS质量、定位误差等

### 交互式地图 ⭐ v2.1自动输出

**自动生成**（v2.1新增）：

运行检测后**自动生成并可选自动打开**！

**输出文件**：

- `data/output/map.html` - 双击打开或在浏览器中查看

**手动生成**（兼容旧方式）：

```bash
python tools/quick_visualize.py data/output/geojson/detections_unique.geojson
```

**功能特性**：

- ✅ 检测框多边形显示（颜色区分类别）
- ✅ 透明度反映置信度（高置信度更明显）
- ✅ 点击弹窗显示详细信息（坐标、GPS质量、定位误差）
- ✅ 类别图例和统计数量
- ✅ 自动缩放到检测区域
- ✅ 基于Leaflet.js，支持缩放、平移、测距

**地图底图**：

- 默认：OpenStreetMap
- 可修改为：天地图、高德地图等（需修改 `map_generator.py`）

### 智能去重功能 ⭐ v2.1新增

**问题背景**：

实时模式下，同一目标可能被检测几十甚至上百次，导致：
- CSV数据冗余（1小时可能上万条记录）
- GeoJSON文件过大（影响GIS软件加载速度）
- 地图上检测框重叠（可视化效果差）

**解决方案**：

在后处理阶段自动执行智能去重，保留最佳检测：

1. **空间分组**：距离<5米的检测归为同一目标
2. **质量评分**：综合考虑置信度、边缘位置、GPS质量、定位误差
3. **保留最佳**：每组选择质量评分最高的检测

**质量评分公式**：

```
评分 = 置信度 × 边缘系数 × GPS质量系数 × 误差系数

其中：
- 边缘系数：0.5（边缘）/ 1.0（中央）→ 优先保留完整目标
- GPS质量系数：1.2（RTK）/ 1.0（HIGH）/ 0.7（LOW）
- 误差系数：1.0（<5m）/ 0.9（5-10m）/ 0.8（>10m）
```

**效果对比**：

| 场景 | 原始检测数 | 去重后 | 去重率 | 效果 |
|------|-----------|--------|--------|------|
| 离线视频（5分钟） | 523 | 156 | 70% | 数据清晰，无冗余 |
| 实时流（1小时） | ~18,000 | ~600 | 97% | 极大优化 |

**配置控制**：

```yaml
# config/offline_config.yaml
output:
  enable_deduplication: true       # 开启/关闭去重
  deduplication:
    distance_threshold: 5.0        # 距离阈值（米）
    prefer_non_edge: true          # 优先中央检测
    min_quality_score: 0.3         # 最低质量阈值
```

### 统计摘要 ⭐ v2.1新增

**自动生成**：

运行检测后自动生成 `data/output/summary.txt`

**内容包括**：

- 检测数量统计（原始、去重后）
- 按类别统计（数量、占比）
- 置信度统计（平均、最高、最低、中位数）
- 地理坐标范围（纬度、经度、高度、覆盖面积）
- GPS质量统计（RTK/HIGH/MEDIUM/LOW分布）
- 边缘检测统计（边缘检测数、完整检测数）

### 检测截图

**保存位置**：

- 视频模式：`data/output/images/offline/`
- 实时模式：`data/output/images/realtime/`

**文件命名**：

```
frame_帧号_obj_序号_类别名_时间戳.jpg

示例：
frame_000123_obj_001_Vegetation_20260210_103015_456.jpg
```

**内容**：

- 完整帧画面
- 绘制检测框
- 显示类别标签和置信度

---

## 验证流程

### 自动验证流程（推荐）

**Windows用户**：

```bash
run_validation.bat
```

这个脚本会自动完成：

1. ✓ 导出GeoJSON格式
2. ✓ 在浏览器中打开交互式地图
3. ✓ （可选）抽样验证坐标准确度
4. ✓ 生成Markdown提交报告

### 手动验证步骤

**v2.1简化流程**（推荐）：

检测完成后**已自动生成**GeoJSON和地图，可以直接：

**步骤1：查看可视化地图**

```bash
# 双击打开自动生成的地图
start data/output/map.html

# 或在配置文件中设置 auto_open_map: true，检测完成后自动打开
```

**步骤2：在GIS软件中验证**

```bash
# 在QGIS中打开
# 图层 → 添加图层 → 矢量图层 → 选择：
data/output/geojson/detections_unique.geojson  # 推荐：去重后的干净数据
```

**步骤3：查看统计摘要**

```bash
# 查看自动生成的统计信息
notepad data/output/summary.txt
```

**v2.0传统流程**（兼容）：

如果需要手动生成或自定义参数：

**步骤1：导出GeoJSON**

```bash
python tools/export_to_geojson.py data/output/csv/detections_offline.csv --min-confidence 0.5
```

**步骤2：查看地图**

```bash
python tools/quick_visualize.py
```

**步骤3：坐标准确度验证（可选）**

```bash
python tools/sample_validation.py --samples 20 --csv data/output/csv/detections_offline.csv
```

**步骤4：生成提交报告**

```bash
python tools/generate_report.py --csv data/output/csv/detections_offline.csv
```

---

## 故障排查

### 问题1：FFmpeg未找到

**症状**：

```
FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'
```

**解决方案**：

```bash
# Windows
choco install ffmpeg -y

# 或手动安装
# 1. 下载：https://ffmpeg.org/download.html
# 2. 解压到 C:\ffmpeg
# 3. 添加环境变量：C:\ffmpeg\bin

# 验证
ffmpeg -version
```

### 问题2：CUDA不可用

**症状**：

```
[WARNING] CUDA not available, using CPU
```

**解决方案**：

```bash
# 安装CUDA版PyTorch
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 验证
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### 问题3：坐标偏差很大

**症状**：检测框位置偏移>100米

**排查步骤**：

1. **检查相机参数**：确认 `config/camera_params.yaml` 中的参数与实际相机一致
2. **检查高度数据**：确认SRT/MQTT中的altitude字段正确
3. **查看时间同步**：检查日志中的时间差是否<100ms
4. **测试样本**：使用已知地标验证转换算法

**临时修正**：

如果发现系统性偏差（如全部向东偏移50米），可以在输出前添加修正：

```python
# 在 coord_transform.py 中添加经验性修正
target_lon = target_lon - 0.00045  # 向西修正50米
```

### 问题4：检测不到目标

**症状**：CSV文件为空或检测数量为0

**排查清单**：

- [ ] 模型文件存在：`models/yolov11x.pt`
- [ ] 置信度不要太高：`yolo_config.yaml` 中 `confidence_threshold: 0.25`
- [ ] 目标类别未过滤：`target_classes: null`
- [ ] 图像尺寸合适：`imgsz: 1280`
- [ ] 视频清晰度足够：检查视频是否模糊或遮挡

**测试方法**：

```bash
# 用一张清晰图片测试模型
python -c "from ultralytics import YOLO; model = YOLO('models/yolov11x.pt'); model.predict('test.jpg', save=True)"
```

### 问题5：CSV写入失败

**症状**：

```
PermissionError: [Errno 13] Permission denied: 'data/output/csv/detections_offline.csv'
```

**解决方案**：

1. 关闭Excel或其他正在打开CSV文件的软件
2. 检查文件夹权限
3. 删除旧的CSV文件
4. 如果还是失败，重启程序

### 问题6：实时模式连接失败

**症状**：

```
[ERROR] Failed to connect to MQTT broker
[ERROR] RTSP stream timeout
```

**排查清单**：

- [ ] 网络连接正常
- [ ] 无人机已开机并连接
- [ ] RTSP地址正确：`rtsp://192.168.xxx.xxx:8554/live`
- [ ] MQTT参数正确：broker、username、password
- [ ] 防火墙未阻止连接
- [ ] SN号已正确替换

**测试方法**：

```bash
# 测试RTSP流
ffplay rtsp://192.168.1.100:8554/live

# 测试MQTT连接（需要mosquitto客户端）
mosquitto_sub -h mqtt.dji.com -p 1883 -u username -P password -t test
```

---

## 项目交接清单

### 文件交付

- [ ] **源代码**：`src/` 目录完整（v2.1新增4个输出模块）
- [ ] **配置文件**：`config/` 目录（v2.1已更新后处理配置）
- [ ] **模型文件**：`models/yolov11x.pt`
- [ ] **依赖列表**：`requirements.txt`
- [ ] **系统文档**：
  - [ ] `README.md` - 项目主文档
  - [ ] `README_VIDEO.md` - 视频处理详细文档
  - [ ] `QUICKSTART.md` - 快速开始指南
- [ ] **v2.0文档**：
  - [ ] `增强版坐标转换实现方案.md` - 3D姿态修正技术方案
  - [ ] `增强版转换器使用指南.md` - 坐标转换配置指南
- [ ] **v2.1文档**（新增）：
  - [ ] `GeoJSON输出和智能去重实现文档.md` - 后处理技术文档
  - [ ] `GeoJSON和地图输出使用指南.md` - GIS输出操作手册
  - [ ] `v2.1功能快速启动指南.md` - 5分钟上手指南
  - [ ] `CHANGELOG_v2.1.md` - 版本更新日志
  - [ ] `v2.1实施完成报告.md` - 功能实施报告
  - [ ] `v2.1实施清单.md` - 实施检查清单
- [ ] **快捷脚本**：`run_*.py`, `run_*.bat`
- [ ] **验证工具**：`tools/` 目录
- [ ] **测试脚本**（v2.1新增）：
  - [ ] `test_post_processing.py` - 后处理功能测试
  - [ ] `test_v2.1_features.bat` - Windows一键测试
- [ ] **示例数据**（可选）：样例视频和处理结果

### 知识转移要点

**必须讲解的内容**：

1. ✅ 两种工作模式的选择（何时用视频，何时用实时流）
2. ✅ 相机参数的重要性及调整方法
3. ✅ 坐标转换原理（GSD计算、像素→GPS）
4. ✅ 常见故障排查流程
5. ✅ 结果验证方法
6. ✅ 配置文件各参数的含义

**演示操作**：

1. ✅ 运行一次完整的视频处理流程
2. ✅ 查看输出结果（CSV、地图）
3. ✅ 调整配置参数（如置信度、跳帧数）
4. ✅ 故障排查（如模拟FFmpeg未安装）

### 环境配置文档

提供详细的环境配置记录：

```
操作系统：Windows 11
Python版本：3.9.13
CUDA版本：11.8
GPU型号：RTX 3050 6GB
Conda环境名：drone_inspection
关键依赖版本：
  - torch: 2.1.0+cu118
  - ultralytics: 8.0.x
  - opencv-python: 4.8.x
  - paho-mqtt: 1.6.x
```

### 技术支持

**联系方式**：

- 项目负责人：[请填写姓名]
- 联系邮箱：[请填写邮箱]
- 技术文档：本README.md + README_VIDEO.md

**已知问题**：

- 相机参数可能需要根据实际设备微调
- 简化版转换器在姿态倾斜时精度下降（建议使用增强版）
- 增强版转换器需要完整的pitch/yaw/roll姿态数据
- 实时模式需要稳定的网络连接

**v2.0更新内容**：

- ✅ 新增增强版坐标转换器（精度提升60-70%）
- ✅ 支持完整3D姿态修正
- ✅ GPS质量控制和RTK识别
- ✅ CSV输出增加质量信息列
- ✅ 向后兼容，可配置切换版本

---

## 许可证

本项目仅供学习和研究使用。

---

**开发团队**: Drone Inspection Team  
**版本**: v2.1.0  
**最后更新**: 2026-02-25

**版本历史**：

| 版本 | 日期 | 主要更新 |
|------|------|---------|
| v2.1.0 | 2026-02-25 | ✅ 智能去重（数据量减少70-97%）<br/>✅ GeoJSON自动导出（3个版本）<br/>✅ HTML地图自动生成（Leaflet.js）<br/>✅ 统计摘要自动生成 |
| v2.0.0 | 2026-02-20 | ✅ 增强版坐标转换（3D姿态修正）<br/>✅ GPS质量控制<br/>✅ 定位误差估算 |
| v1.0.0 | 2026-02-15 | ✅ 基础检测功能<br/>✅ 简化版坐标转换<br/>✅ CSV和截图输出 |

**v2.1详细更新**：
- 智能去重功能（自动去除重复检测，保留最佳质量）
- GeoJSON自动导出（无需手动运行工具，支持QGIS/ArcGIS）
- HTML地图自动生成（Leaflet交互式地图，可选自动打开）
- 统计摘要自动生成（数据概览和质量分析报告）
- 完全向后兼容（所有新功能可选启用）
