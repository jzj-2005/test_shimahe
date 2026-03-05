# 无人机水利四乱巡检系统

基于YOLOv11深度学习的无人机目标检测系统，自动计算检测目标的GPS地理坐标。支持离线视频处理和实时流处理两种模式。

## 目录

- [项目概述](#项目概述)
- [快速开始](#快速开始)
- [目录结构](#目录结构)
- [工作模式详解](#工作模式详解)
- [OCR飞行数据提取功能](#ocr飞行数据提取功能)
- [增强版坐标转换器（v2.0新增）](#增强版坐标转换器v20新增)
- [ByteTrack目标跟踪去重（v2.2新增）](#bytetrack目标跟踪去重v22新增)
- [配置文件详解](#配置文件详解)
- [输出文件说明](#输出文件说明)
- [验证流程](#验证流程)
- [故障排查](#故障排查)
- [项目交接清单](#项目交接清单)

---

## 项目概述

### 核心功能

- ✅ **离线视频处理**：处理本地DJI视频文件+SRT字幕，快速验证算法
- ✅ **实时流处理**：接收RTSP视频流+HTTP/MQTT/OCR位姿数据，实时检测和输出
- ✅ **多源OSD数据接入**：支持HTTP接口、MQTT直连、OCR识别三种位姿数据获取方式，auto模式自动切换
- ✅ **OCR飞行数据提取**：支持从视频画面OSD识别GPS、高度等信息（无需SRT字幕）
- ✅ **YOLOv11目标检测**：高精度目标检测，支持HBB水平框和OBB旋转框两种模式
- ✅ **ByteTrack目标跟踪去重**（v2.2新增）：推理阶段跟踪+延迟保存，从源头消除重复检测
- ✅ **坐标转换**：像素坐标→CGCS2000地理坐标（符合国家标准GB/T 18522-2020）
- ✅ **增强版坐标转换**（v2.0新增）：支持完整3D姿态修正和GPS质量控制，精度提升60-70%
- ✅ **CSV报告输出**：结构化数据导出，包含四角点地理坐标和GPS质量信息
- ✅ **智能去重**（v2.1新增）：后处理阶段自动去除重复检测，保留最佳质量目标
- ✅ **GeoJSON自动导出**（v2.1新增）：检测完成后自动生成GIS矢量数据，支持QGIS/ArcGIS
- ✅ **可视化地图自动生成**（v2.1新增）：自动生成交互式HTML地图，可浏览器查看
- ✅ **检测截图保存**：自动保存检测目标图像
- ✅ **实时可视化**：显示检测框、GPS信息、处理速度等
- ✅ **模型训练工具**：支持自定义数据集训练OBB/HBB模型

### 两种工作模式对比

| 特性 | 视频处理模式 | 实时流处理模式 |
|------|-------------|---------------|
| **适用场景** | 算法验证、效果测试 | 实际巡检作业 |
| **数据源** | 本地视频(.MP4) + SRT字幕/OCR | RTSP视频流 + HTTP/MQTT/OCR位姿 |
| **位姿获取** | SRT优先，OCR备用 | HTTP优先→MQTT备用→OCR兜底（auto模式） |
| **时间同步** | 精确(<100ms) | 实时同步 |
| **处理速度** | 可跳帧加速 | 实时处理 |
| **跟踪去重** | 支持（v2.2） | 支持（v2.2） |
| **优势** | 可重复测试、结果稳定 | 即时反馈、无需存储 |
| **启动命令** | `python run_offline.py` | `python run_realtime.py` |

### 系统架构

```
                        ┌─────────────┐
                        │   视频源     │
                        │ MP4 / RTSP  │
                        └──────┬──────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                 ▼
        ┌──────────┐   ┌──────────┐    ┌──────────────┐
        │ SRT字幕   │   │ HTTP OSD │    │  MQTT OSD    │
        │ (离线)    │   │ (实时优先) │    │  (实时备用)   │
        └────┬─────┘   └────┬─────┘    └──────┬───────┘
             │              │                  │
             │    ┌─────────┴──────────────────┘
             │    │    ┌──────────┐
             │    │    │ OCR备用   │ ← 所有方式不可用时启用
             │    │    └────┬─────┘
             ▼    ▼         ▼
        ┌────────────────────────┐
        │     数据同步 (帧↔位姿)   │
        └───────────┬────────────┘
                    ▼
        ┌────────────────────────┐
        │  YOLO检测 + ByteTrack  │ ← v2.2: 跟踪去重，每个目标只保存最优检测
        └───────────┬────────────┘
                    ▼
        ┌────────────────────────┐
        │   坐标转换 (像素→GPS)   │ ← v2.0: 3D姿态修正 + GPS质量控制
        └───────────┬────────────┘
                    ▼
        ┌────────────────────────┐
        │      结果输出           │
        │  CSV / 截图 / GeoJSON  │ ← v2.1: 自动后处理
        │  地图 / 统计摘要        │
        └────────────────────────┘
```

### 技术栈

- Python 3.9 ~ 3.11
- Ultralytics YOLOv11（>=8.3.0）+ ByteTrack 目标跟踪
- PyTorch（CUDA 11.8+ / 12.1+）
- PaddleOCR（视频OSD文字识别）
- pyproj + scipy（CGCS2000坐标转换与3D旋转）
- OpenCV（视频处理）
- Paho-MQTT（MQTT通信）
- Requests（HTTP OSD数据获取）
- FFmpeg（SRT提取）
- Folium / Leaflet.js（地图可视化）
- Loguru（日志系统）
- Pandas / NumPy（数据处理）

### 相关文档

**v2.2文档**：

- [v2.2_tracking_dedup_report.md](v2.2_tracking_dedup_report.md) - 推理阶段跟踪去重实施报告

**v2.1文档**：

- [GeoJSON输出和智能去重实现文档.md](GeoJSON输出和智能去重实现文档.md) - 技术实现细节、算法原理
- [GeoJSON和地图输出使用指南.md](GeoJSON和地图输出使用指南.md) - 操作手册、配置指南
- [CHANGELOG_v2.1.md](CHANGELOG_v2.1.md) - v2.1版本更新日志

**v2.0文档**：

- [增强版坐标转换实现方案.md](增强版坐标转换实现方案.md) - 3D姿态修正技术方案
- [增强版转换器使用指南.md](增强版转换器使用指南.md) - 坐标转换配置指南

**其他文档**：

- [docs/SOP_AI视觉四乱目标检测解决方案.md](docs/SOP_AI视觉四乱目标检测解决方案.md) - 完整解决方案SOP
- [docs/HTTP_OSD_配置说明.md](docs/HTTP_OSD_配置说明.md) - HTTP OSD接口对接指南
- [docs/DJI_MQTT_SETUP.md](docs/DJI_MQTT_SETUP.md) - DJI无人机MQTT配置指南
- [docs/model_training_guide.md](docs/model_training_guide.md) - 模型训练指南

---

## 快速开始

### 1. 环境准备

**前置条件清单：**

- [ ] Windows 10/11 或 Linux
- [ ] Python 3.9 ~ 3.11 已安装
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

下载训练好的YOLOv11模型：

```bash
# 将模型文件放入 models/ 目录
models/
└── yolov11x.pt  # 确保此文件存在
```

### 4. 第一次运行（视频处理示例）

```bash
# 使用Python脚本
python run_offline.py "data/input/videos/测试视频.MP4"

# 或使用完整命令
python -m src.main --mode offline --video "data/input/videos/测试视频.MP4"

# 运行后查看输出
data/output/csv/detections_offline.csv       # CSV结果
data/output/images/                          # 检测截图
```

### 5. 查看结果

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

### 6. 运行前检查（可选）

```bash
# 检查环境和依赖是否就绪
python check_before_run.py
```

---

## 目录结构

```
siluan_new/                                  # 项目根目录
│
├── 📁 config/                               # ⭐ 所有配置文件
│   ├── camera_params.yaml                  # [重要] 相机参数（影响坐标准确性）
│   ├── yolo_config.yaml                    # YOLO检测 + 跟踪配置
│   ├── offline_config.yaml                 # 视频处理配置（跳帧、输出设置）
│   ├── offline_config_demo.yaml            # 视频处理配置示例（含详细注释）
│   ├── realtime_config.yaml                # 实时流配置（RTSP、HTTP/MQTT、OSD源）
│   ├── realtime_config.example.yaml        # 实时流配置模板
│   ├── bytetrack.yaml                      # [v2.2] ByteTrack跟踪器参数
│   ├── training_config.yaml                # 模型训练配置
│   └── simulation_config.yaml              # 模拟测试配置
│
├── 📁 src/                                  # ⭐ 核心源代码
│   │
│   ├── 📁 input/                            # 数据输入层
│   │   ├── base_reader.py                  # 读取器基类（统一接口）
│   │   ├── video_file_reader.py            # [离线] 读取本地MP4视频
│   │   ├── srt_extractor.py                # [离线] 从视频提取SRT字幕
│   │   ├── srt_parser.py                   # [离线] 解析SRT获取GPS数据
│   │   ├── osd_ocr_reader.py               # [备用] OCR识别视频OSD飞行数据
│   │   ├── rtsp_stream_reader.py           # [实时] 读取RTSP视频流
│   │   ├── http_osd_client.py              # [实时] HTTP接口获取OSD位姿数据
│   │   └── mqtt_client.py                  # [实时] MQTT接收OSD位姿数据
│   │
│   ├── 📁 detection/                        # 检测与跟踪层
│   │   ├── yolo_detector.py                # YOLOv11目标检测（HBB/OBB + 跟踪）
│   │   └── track_manager.py                # [v2.2] 跟踪去重管理器（延迟保存策略）
│   │
│   ├── 📁 transform/                        # 坐标转换层
│   │   ├── camera_model.py                 # 相机参数模型（GSD计算）
│   │   ├── coord_transform.py              # 像素→GPS坐标转换（简化版）
│   │   └── coord_transform_new.py          # [v2.0] 增强版转换器（3D姿态修正）
│   │
│   ├── 📁 output/                           # 输出层
│   │   ├── csv_writer.py                   # CSV报告生成（CGCS2000坐标）
│   │   ├── image_saver.py                  # 检测截图保存
│   │   ├── report_generator.py             # 汇总报告 + 后处理调度
│   │   ├── post_processor.py               # [v2.1] 后处理流程编排
│   │   ├── deduplication.py                # [v2.1] 空间去重（Haversine距离）
│   │   ├── geojson_writer.py               # [v2.1] GeoJSON矢量数据导出
│   │   └── map_generator.py                # [v2.1] HTML交互式地图生成
│   │
│   ├── 📁 utils/                            # 工具模块
│   │   ├── data_sync.py                    # 时间戳同步（帧↔位姿匹配）
│   │   ├── visualizer.py                   # 实时可视化显示
│   │   ├── logger.py                       # 日志系统（loguru）
│   │   └── config_loader.py                # 配置文件加载
│   │
│   ├── offline_pipeline.py                  # ⭐ [入口] 视频处理完整流程
│   ├── realtime_pipeline.py                 # ⭐ [入口] 实时流处理完整流程
│   └── main.py                              # 主程序入口（命令行接口）
│
├── 📁 tools/                                # ⭐ 辅助工具
│   ├── export_to_geojson.py                # 手动导出GeoJSON（兼容旧流程）
│   ├── sample_validation.py                # 坐标准确度验证
│   ├── generate_report.py                  # 生成Markdown提交报告
│   ├── train_model.py                      # 模型训练脚本
│   ├── extract_training_frames.py          # 从视频提取训练帧
│   ├── evaluate_model.py                   # 模型评估
│   ├── mock_mqtt_publisher.py              # MQTT模拟发布（测试用）
│   └── test_http_osd.py                    # HTTP OSD接口测试
│
├── 📁 models/                               # ⭐ 模型文件
│   └── yolov11x.pt                         # YOLOv11x权重文件（必需）
│
├── 📁 data/                                 # 数据目录
│   ├── input/videos/                       # 输入视频存放处
│   ├── temp/srt/                           # 临时SRT文件
│   ├── dataset.yaml                        # 训练数据集配置
│   └── output/                             # ⭐ 所有输出结果
│       ├── csv/                            # CSV检测报告
│       ├── images/                         # 检测截图
│       ├── geojson/                        # [v2.1] GIS矢量数据
│       │   ├── detections_raw.geojson      #   原始完整数据
│       │   ├── detections_unique.geojson   #   智能去重数据（推荐）
│       │   └── detections_high_conf.geojson#   高置信度数据
│       ├── map.html                        # [v2.1] 可视化地图
│       └── summary.txt                     # [v2.1] 统计摘要
│
├── 📁 docs/                                 # 文档
│   ├── DJI_MQTT_SETUP.md                   # DJI无人机MQTT配置指南
│   ├── HTTP_OSD_配置说明.md                  # HTTP OSD接口对接指南
│   ├── SOP_AI视觉四乱目标检测解决方案.md      # 完整解决方案SOP
│   └── model_training_guide.md             # 模型训练指南
│
├── 📁 tests/                                # 测试文件
│   ├── test_coord_transform_new.py         # 增强版转换器单元测试
│   ├── test_cgcs2000_conversion.py         # CGCS2000转换测试
│   ├── test_post_processing.py             # 后处理功能测试
│   ├── test_mqtt_realtime.py               # MQTT实时测试
│   ├── test_rtsp_connection.py             # RTSP连接测试
│   ├── test_sync_altitude.py               # 高度同步测试
│   └── quick_visualize.py                  # 快速可视化工具
│
├── 📁 archived/                             # 归档文件
│   ├── docs/                               # 旧版文档
│   ├── scripts/                            # 旧版安装脚本
│   └── tests/                              # 旧版测试脚本
│
├── 📄 run_offline.py                        # ⭐ [快捷启动] 视频处理
├── 📄 run_realtime.py                       # ⭐ [快捷启动] 实时流处理
├── 📄 check_before_run.py                   # 运行前环境检查
├── 📄 verify_v2.1_installation.py           # v2.1安装验证
├── 📄 video_frame_split.py                  # 视频帧分割工具
├── 📄 test_v2.1_features.bat                # [Windows] v2.1功能测试
│
├── 📄 requirements.txt                      # Python依赖列表
├── 📄 README.md                             # ⭐ 项目主文档（本文件）
├── 📄 README_VIDEO.md                       # 视频处理详细文档
├── 📄 CHANGELOG_v2.1.md                     # v2.1版本更新日志
├── 📄 增强版坐标转换实现方案.md               # [v2.0] 转换器技术方案
├── 📄 增强版转换器使用指南.md                 # [v2.0] 转换器使用手册
├── 📄 GeoJSON输出和智能去重实现文档.md        # [v2.1] 后处理技术文档
├── 📄 GeoJSON和地图输出使用指南.md            # [v2.1] GIS输出操作手册
└── 📄 v2.2_tracking_dedup_report.md         # [v2.2] 跟踪去重实施报告
```

**目录说明：**

- ⭐ 标记的是最重要的文件/目录
- [离线] 标记的仅用于视频处理模式
- [实时] 标记的仅用于实时流模式
- [备用] 标记的在主数据源不可用时自动启用
- [v2.x] 标记的是对应版本新增内容

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

**方法A：Python脚本（推荐）**

```bash
python run_offline.py "data/input/videos/DJI_0001.MP4"
```

**方法B：完整命令（更多参数）**

```bash
python -m src.main --mode offline --video "data/input/videos/DJI_0001.MP4" --config ./config
```

#### 1.4 处理流程

```
1. [SRT提取] 自动从视频提取SRT字幕（使用FFmpeg）
   ↓  如果SRT不可用，自动切换OCR模式
2. [数据解析] 解析SRT/OCR，提取每帧的GPS、高度、姿态数据
   ↓
3. [视频解码] 逐帧读取视频（支持跳帧加速）
   ↓
4. [时间同步] 将视频帧与位姿数据精确匹配（<100ms误差）
   ↓
5. [目标检测] YOLO检测 + ByteTrack跟踪（v2.2：同一目标只保存最优检测）
   ↓
6. [坐标转换] 将检测框像素坐标转换为CGCS2000地理坐标
   ↓
7. [结果输出] CSV + 截图 + GeoJSON + 地图 + 统计摘要（自动后处理）
```

#### 1.5 配置调整

编辑 [`config/offline_config.yaml`](config/offline_config.yaml)：

```yaml
# 视频处理
video_processing:
  frame_skip: 15             # 跳帧处理（15=每15帧处理1帧，河岸四乱检测推荐）
  start_frame: 0             # 从第几帧开始
  end_frame: 0               # 到第几帧结束（0=处理到最后）
  show_progress: true        # 显示进度条

# OCR配置（SRT不可用时生效）
ocr:
  enabled: true              # 启用OCR备用
  frame_interval: 15         # 与frame_skip保持一致

# 数据同步
data_sync:
  sync_method: "timestamp"   # 同步方式
  timestamp_tolerance: 100   # 时间容差(ms)

# 输出控制
output:
  save_images: true          # 是否保存检测截图
  image_format: "full"       # full=全帧标注图，crop=仅目标区域
  export_geojson: true       # 自动导出GeoJSON
  enable_deduplication: true # 智能去重
  generate_map: true         # 生成交互式地图
  generate_summary: true     # 生成统计摘要
  auto_open_map: false       # 是否自动打开地图

# 可视化
visualization:
  realtime_display: true     # 是否实时显示处理画面
  display_width: 1280        # 显示窗口宽度
```

#### 1.6 输出结果

```
data/output/
├── csv/
│   └── detections_offline.csv                    # ⭐ CSV检测报告
├── images/
│   ├── frame_000001_obj_001_Vegetation_20260210_103015.jpg
│   └── ...                                       # 检测截图
├── geojson/                                      # ⭐ GIS数据
│   ├── detections_raw.geojson                    # 原始完整数据
│   ├── detections_unique.geojson                 # 智能去重数据（推荐）
│   └── detections_high_conf.geojson              # 高置信度数据
├── map.html                                      # ⭐ 可视化地图
├── summary.txt                                   # ⭐ 统计摘要
└── offline_log.txt                               # 处理日志
```

### 模式2：实时流处理（实际巡检场景）

#### 2.1 适用场景

- ✅ 实际巡检作业
- ✅ 实时目标反馈
- ✅ 无需存储大量视频

#### 2.2 OSD数据源（位姿数据获取）

实时模式支持三种位姿数据源，通过 `osd_source` 配置选择：

| 数据源 | 配置值 | 说明 | 适用场景 |
|--------|-------|------|---------|
| **HTTP接口** | `"http"` | 通过HTTP轮询获取OSD数据（开发部桥接服务） | 有HTTP桥接服务时优先使用 |
| **MQTT直连** | `"mqtt"` | 直连DJI Cloud API MQTT获取OSD数据 | 直连DJI云平台 |
| **自动切换** | `"auto"` | HTTP优先，失败自动降级到MQTT，再降级到OCR | **推荐配置** |

#### 2.3 前置配置

**步骤1：选择OSD数据源并配置**

编辑 [`config/realtime_config.yaml`](config/realtime_config.yaml)：

```yaml
# OSD数据源选择（推荐auto）
osd_source: "auto"          # http / mqtt / auto

# HTTP OSD接口配置（osd_source为http或auto时需要）
http_osd:
  base_url: "http://10.5.52.129:10006"
  api_path: "/satxspace-airspace/ai/getDrone"
  dev_sn: "1581F8HGX25B500A11XF"   # 设备SN
  poll_interval: 0.1                 # 轮询间隔(秒)，0.1=10Hz
  request_timeout: 2                 # 请求超时(秒)
  max_retry: 3                       # 连续失败N次后降级到MQTT

# RTSP视频流配置
rtsp:
  url: "rtsp://192.168.1.100:8554/live"  # [必改] RTSP流地址
  reconnect_interval: 5
  buffer_size: 30
  transport_protocol: "tcp"

# MQTT配置（osd_source为mqtt或auto时需要）
mqtt:
  broker: "mqtt-cn.dji.com"           # [必改] MQTT服务器
  port: 1883
  username: "[请填写DJI App Key]"      # [必改]
  password: "[请填写DJI App Secret]"   # [必改]
  client_id: "drone_inspection_001"
  topics:
    aircraft_state: "thing/product/[设备SN]/osd"  # [必改] 替换设备SN
```

参考 [`docs/DJI_MQTT_SETUP.md`](docs/DJI_MQTT_SETUP.md) 和 [`docs/HTTP_OSD_配置说明.md`](docs/HTTP_OSD_配置说明.md) 获取详细配置说明。

#### 2.4 启动方法

```bash
conda activate drone_inspection

# 启动实时处理
python run_realtime.py

# 或使用完整命令
python -m src.main --mode realtime --config ./config
```

#### 2.5 运行状态

启动后会看到（以auto模式为例）：

```
[INFO] OSD数据源: auto (HTTP优先，MQTT备用)
[INFO] 连接HTTP OSD: http://10.5.52.129:10006
[INFO] 连接RTSP流: rtsp://192.168.1.100:8554/live
[INFO] 开始实时处理 [帧率: 25fps]
[INFO] 检测到目标: Vegetation, 置信度: 0.85, GPS: (22.779814, 114.101319)
```

如果HTTP连接失败，自动降级：

```
[WARNING] HTTP OSD连续失败3次，降级到MQTT
[INFO] 连接MQTT: mqtt-cn.dji.com:1883
```

#### 2.6 实时输出

```
data/output/
├── csv/
│   └── detections_realtime.csv         # 实时追加检测结果
├── images/
│   └── detection_20260210_103015_001.jpg
├── summary.txt                          # 统计摘要（默认开启）
└── realtime_log.txt                     # 实时日志

注意：实时模式的GeoJSON和地图默认关闭（数据量大），可在配置中开启
```

#### 2.7 停止处理

按 `Ctrl+C` 或 `Esc` 键安全退出。退出时会自动flush所有跟踪缓冲并执行后处理。

---

## OCR飞行数据提取功能

### 功能概述

系统支持使用OCR（光学字符识别）从视频画面的OSD（屏幕显示）区域提取飞行数据，作为SRT字幕的替代方案。

**使用场景：**
- ✅ 视频文件不包含SRT字幕轨道
- ✅ 无法从视频中提取字幕数据
- ✅ 实时模式下HTTP和MQTT数据均不可用时的兜底方案

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
    width: 800               # 推荐800以捕获完整数据（含小数）
    height: 300

  frame_interval: 15         # 每N帧识别一次（与frame_skip保持一致）
  use_gpu: true              # 是否使用GPU加速
```

**实时模式配置** (`config/realtime_config.yaml`):

```yaml
ocr_fallback:
  enabled: true              # 启用OCR备用
  frame_interval: 10         # 实时模式建议更大间隔
  use_gpu: false             # 实时模式OCR建议CPU（GPU留给YOLO）
```

### 性能对比

| 指标 | SRT模式 | OCR模式 |
|------|---------|---------|
| **准确度** | ★★★★★ | ★★★★☆ |
| **速度** | ★★★★★ | ★★★☆☆ |
| **GPU占用** | 低 | 中 |
| **适用场景** | 优先推荐 | 备用方案 |

### ROI区域调整

如果OCR识别效果不佳，可能需要调整ROI区域：

| ROI宽度 | 识别效果 |
|---------|----------|
| 600像素 | ❌ 高度只有整数（如139） |
| 800像素 | ✅ 完整精度（如139.365m） |

**调整步骤：**

1. 播放视频，确认OSD文字位置（通常在左上角）
2. 修改配置文件中的ROI参数
3. 重新运行测试

### 首次运行说明

PaddleOCR首次运行时会自动下载模型文件（约10MB），请确保网络连接正常。模型文件会缓存在本地，后续运行无需重复下载。

---

## 增强版坐标转换器（v2.0新增）

### 功能概述

增强版坐标转换器实现了完整的3D姿态修正和GPS质量控制，将检测目标定位精度从**5-10米提升到2-3米**，改善幅度达到**60-70%**。

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
python run_offline.py "视频路径.MP4"  # 或 python run_realtime.py
```

系统会自动：
- ✅ 使用3D姿态修正算法
- ✅ 评估GPS质量并过滤低质量数据
- ✅ 在CSV中添加质量信息列

### OSD数据要求

为了充分利用增强版功能，位姿数据需要包含完整的姿态信息：

**必需字段**：
```json
{
  "latitude": 22.779954,
  "longitude": 114.100891,
  "altitude": 139.231,
  "pitch": -88.5,
  "yaw": 45.2,
  "roll": 0.1
}
```

**推荐字段**（质量控制）：
```json
{
  "gps_level": 5,
  "satellite_count": 18,
  "positioning_state": "RTK_FIXED"
}
```

### CSV新增字段

增强版转换器在CSV输出中添加的质量信息列：

| 列名 | 说明 | 示例值 |
|------|------|--------|
| `gps_quality` | GPS质量等级 | RTK / HIGH / MEDIUM / LOW |
| `positioning_state` | 定位状态 | RTK_FIXED / GPS / DGPS |
| `estimated_error` | 预估误差（米） | 0.05 / 2.5 / 5.0 |
| `gps_level` | GPS信号强度 | 0-5 |
| `satellite_count` | 卫星数量 | 18 / 12 / 8 |

### 向后兼容

- 增强版与简化版可通过配置文件灵活切换
- CSV格式完全兼容（新增列在末尾）
- 默认使用简化版，需手动开启增强版

---

## ByteTrack目标跟踪去重（v2.2新增）

### 问题背景

在v2.1之前，YOLO对每一帧独立检测，同一物理目标在连续多帧中被反复检测，导致：
- CSV中存在大量重复记录（同一目标被记录10-50+次）
- 大量冗余的坐标转换计算和图像截图保存
- 后续GeoJSON/地图中出现密集重叠矢量框

v2.1的后处理去重虽然能在输出时清理重复，但前序计算资源已浪费。

### 解决方案

v2.2引入**Ultralytics内置目标跟踪（ByteTrack）+ 延迟保存策略**，从推理阶段根本解决重复问题：

```
视频帧 → YOLO推理 + ByteTrack跟踪 → 检测结果(含track_id)
                                         ↓
                                   TrackManager
                                   ├── 新目标 → 创建缓冲
                                   ├── 已有目标 → 如果质量更优则替换缓冲
                                   └── 消失目标 → 输出最优 → 坐标转换 → CSV + 截图
                                         ↓
                                   管线结束 → flush_all() → 输出所有剩余缓冲
                                         ↓
                                   report_gen.close() → 后处理(GeoJSON/地图/去重)
```

### 质量评分公式

```
score = confidence × edge_factor × (1.0 + area_bonus)

其中:
- edge_factor: 非边缘=1.0，边缘=edge_penalty（默认0.3）
- area_bonus: 目标面积越大越好（上限0.2）
```

### 双重去重机制

v2.2实现了两层去重，效果互补：

| 层级 | 阶段 | 机制 | 效果 |
|------|------|------|------|
| **第1层** | 推理阶段（v2.2） | ByteTrack跟踪 + 延迟保存 | 同一track_id只输出1条，减少90%+ |
| **第2层** | 后处理阶段（v2.1） | 空间距离聚类 + 质量评分 | 跨track_id的近距离重复再清理 |

### 配置参数

在 [`config/yolo_config.yaml`](config/yolo_config.yaml) 中配置：

```yaml
tracking:
  enabled: true               # 启用跟踪去重（关闭则回退到逐帧独立检测）
  tracker: "bytetrack.yaml"   # 跟踪器类型
  lost_threshold: 30          # 目标消失N帧后输出最优检测
  edge_penalty: 0.3           # 边缘目标质量惩罚系数
  min_track_frames: 3         # 最少出现帧数（过滤闪现误检）
  crop_buffer: false          # 是否裁剪缓冲帧（true节省内存，但不支持full模式截图）
```

ByteTrack跟踪器参数（[`config/bytetrack.yaml`](config/bytetrack.yaml)）：

```yaml
tracker_type: bytetrack
track_high_thresh: 0.5        # 高置信度检测匹配阈值
track_low_thresh: 0.1         # 低置信度检测阈值
new_track_thresh: 0.6         # 新建跟踪的最低置信度
track_buffer: 30              # 跟踪缓冲帧数
match_thresh: 0.8             # IoU匹配阈值
```

### 关闭跟踪

如果需要回退到逐帧独立检测（调试等场景）：

```yaml
# config/yolo_config.yaml
tracking:
  enabled: false
```

---

## 配置文件详解

### camera_params.yaml（影响坐标准确性⭐）

**路径**：[`config/camera_params.yaml`](config/camera_params.yaml)

**关键参数**：

```yaml
camera:
  model: "DJI_M4TD"                        # 相机型号
  resolution:
    width: 4032                            # [关键] 必须与实际拍摄分辨率一致
    height: 3024
  sensor_size:
    width: 13.4                            # [关键] 传感器宽度(mm)
    height: 9.6                            # [关键] 传感器高度(mm)
  focal_length: 6.72                       # [关键] 焦距(mm)
  principal_point:
    cx: 2016                               # width / 2
    cy: 1512                               # height / 2
  distortion:                              # 畸变系数（不考虑畸变保持为0）
    k1: 0.0
    k2: 0.0
    p1: 0.0
    p2: 0.0
    k3: 0.0

orthogonal_mode:                           # 正射投影模式
  assume_vertical: true                    # 假设严格垂直拍摄
  pitch: -90.0                             # 俯仰角
  use_attitude_correction: false           # 是否使用姿态角修正

earth:
  meters_per_degree_lat: 110540            # 每度纬度对应的米数
  meters_per_degree_lon: 111320            # 每度经度对应的米数（赤道处）

coordinate_transform:
  use_enhanced: false                      # true=增强版(3D修正)，false=简化版
  quality_control:
    enabled: true
    min_gps_level: 3                       # 最低GPS信号（1-5）
    min_satellite_count: 10                # 最少卫星数
    skip_on_low_quality: true              # 是否跳过低质量数据
  error_estimation:
    enabled: true
    gps_base_error: 3.5                    # 普通GPS基础误差(米)
    rtk_base_error: 0.05                   # RTK基础误差(米)
```

**⚠️ 重要提示**：这些参数直接影响GPS坐标计算精度。如果坐标偏差>100米，首先检查这里的参数。

### yolo_config.yaml（影响检测效果）

**路径**：[`config/yolo_config.yaml`](config/yolo_config.yaml)

```yaml
model:
  path: "./models/yolov11x.pt"           # 模型文件路径
  device: "cuda"                         # cuda=GPU, cpu=CPU
  half_precision: true                   # 半精度加速
  obb_mode: false                        # true=OBB旋转框, false=HBB水平框

detection:
  confidence_threshold: 0.5              # 置信度阈值（河岸四乱推荐0.5减少误检）
  iou_threshold: 0.45                    # NMS阈值
  max_detections: 300                    # 最大检测数
  imgsz: 1280                            # 推理图像尺寸

classes:
  target_classes: null                   # null=所有类别，或指定ID列表如 [0,1,2]
  names:
    0: "Water Bodies"
    1: "Vegetation"
    2: "Mining Area"
    3: "Debris"
    4: "Industrial Buildings"
    5: "Waterway Facilities"
    6: "Hydraulic Controls"
    7: "Residences"
    8: "Sheds"
    9: "Storage Zones"
    10: "Recreation Areas"

tracking:                                # v2.2: 目标跟踪去重
  enabled: true
  tracker: "bytetrack.yaml"
  lost_threshold: 30
  edge_penalty: 0.3
  min_track_frames: 3
  crop_buffer: false
```

**调优建议**：

- **提高检出率**：降低 `confidence_threshold` 到 0.3
- **减少误报**：提高 `confidence_threshold` 到 0.6
- **提高速度**：降低 `imgsz` 到 640
- **提高精度**：提高 `imgsz` 到 1920（需要更多显存）

### offline_config.yaml（视频处理参数）

**关键参数**：

```yaml
video_processing:
  frame_skip: 15             # 跳帧数（河岸四乱检测推荐15）
  start_frame: 0             # 起始帧
  end_frame: 0               # 结束帧（0=处理到最后）
  show_progress: true        # 显示进度条

output:
  save_images: true          # 保存截图
  save_only_with_detections: true  # 只保存有检测结果的图片
  image_format: "full"       # full=全帧标注，crop=仅目标区域

  # v2.1后处理
  export_geojson: true       # GeoJSON导出
  enable_deduplication: true # 智能去重
  generate_map: true         # 交互式地图
  generate_summary: true     # 统计摘要
  auto_open_map: false       # 自动打开地图
```

### realtime_config.yaml（实时流配置）

**关键参数**：

```yaml
# OSD数据源选择
osd_source: "auto"           # http / mqtt / auto（推荐auto）

# HTTP OSD接口
http_osd:
  base_url: "http://..."     # [必改] HTTP服务地址
  dev_sn: "..."              # [必改] 设备SN
  poll_interval: 0.1         # 轮询间隔(秒)
  max_retry: 3               # 失败降级阈值

# RTSP流
rtsp:
  url: "rtsp://..."          # [必改] RTSP流地址
  reconnect_interval: 5      # 断线重连间隔
  buffer_size: 30            # 缓冲区大小
  transport_protocol: "tcp"  # 传输协议

# MQTT
mqtt:
  broker: "mqtt-cn.dji.com"  # [必改] MQTT服务器
  port: 1883
  username: "..."            # [必改] DJI App Key
  password: "..."            # [必改] DJI App Secret
  topics:
    aircraft_state: "thing/product/[设备SN]/osd"

# 实时处理
realtime_processing:
  target_fps: 0              # 0=尽可能快
  frame_skip: 1              # 处理间隔
  enable_multithreading: true

# 输出（实时模式GeoJSON和地图默认关闭）
output:
  csv_write_mode: "append"   # 追加写入
  export_geojson: false      # 实时模式默认关闭
  generate_map: false        # 实时模式默认关闭
  generate_summary: true     # 统计摘要默认开启
```

### bytetrack.yaml（跟踪器参数）

```yaml
tracker_type: bytetrack
track_high_thresh: 0.5       # 高置信度匹配阈值
track_low_thresh: 0.1        # 低置信度阈值
new_track_thresh: 0.6        # 新建跟踪最低置信度
track_buffer: 30             # 目标消失后保持帧数
match_thresh: 0.8            # IoU匹配阈值
```

### 其他配置文件

| 配置文件 | 用途 |
|---------|------|
| `training_config.yaml` | 模型训练参数（task、epochs、imgsz、数据增强等） |
| `simulation_config.yaml` | 模拟测试配置（本地MQTT/RTSP，用于开发调试） |
| `offline_config_demo.yaml` | 离线配置示例（含详细注释，新手参考用） |
| `realtime_config.example.yaml` | 实时配置模板（含示例值） |

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
| **corner2_lat** ~ **corner4_lon** | 浮点数 | 其余三个角点坐标 | ... |
| **center_lat** | 浮点数 | 目标中心纬度 | 22.779814 |
| **center_lon** | 浮点数 | 目标中心经度 | 114.101319 |
| altitude | 浮点数 | 飞行高度(m) | 139.231 |
| drone_lat | 浮点数 | 无人机纬度 | 22.779954 |
| drone_lon | 浮点数 | 无人机经度 | 114.100891 |
| image_path | 字符串 | 截图路径 | ./data/output/images/... |
| **gps_quality** | 字符串 | GPS质量等级（增强版） | RTK / HIGH / MEDIUM |
| **positioning_state** | 字符串 | 定位状态（增强版） | RTK_FIXED / GPS |
| **estimated_error** | 浮点数 | 预估误差米（增强版） | 0.05 / 2.5 / 5.0 |
| **gps_level** | 整数 | GPS信号强度（增强版） | 0-5 |
| **satellite_count** | 整数 | 卫星数量（增强版） | 18 / 12 / 8 |

**注意事项**：

- 四个corner坐标定义了检测框的矩形范围
- center坐标是四个角点的平均值
- **所有坐标均为CGCS2000坐标系**（中国国家标准，EPSG:4490）
- 无人机GPS原始坐标为WGS84，已自动转换为CGCS2000
- 后5列GPS质量信息仅在启用增强版转换器时有值

### GeoJSON文件（用于GIS软件）

**自动生成**（v2.1+）：运行检测后自动生成，无需手动执行脚本。

**输出文件**：

- `data/output/geojson/detections_raw.geojson` - 原始完整数据
- `data/output/geojson/detections_unique.geojson` - **智能去重数据（推荐用于GIS）**
- `data/output/geojson/detections_high_conf.geojson` - 高置信度检测（>0.7）

**手动生成**（兼容旧方式）：

```bash
python tools/export_to_geojson.py data/output/csv/detections_offline.csv
```

**GIS软件使用**：

- **QGIS**: 图层 → 添加图层 → 矢量图层 → 选择 `detections_unique.geojson`
- **ArcGIS**: Add Data → 选择 `.geojson` 文件
- **坐标系**: CGCS2000 (EPSG:4490)，几何类型: Polygon

### 交互式地图

**自动生成**（v2.1+）：`data/output/map.html`，双击打开或在浏览器中查看。

**功能特性**：

- ✅ 检测框多边形显示（颜色区分类别）
- ✅ 透明度反映置信度
- ✅ 点击弹窗显示详细信息
- ✅ 类别图例和统计数量
- ✅ 基于Leaflet.js，支持缩放、平移

### 智能去重功能

**双重去重机制**（v2.1 + v2.2）：

**第1层 - 推理阶段跟踪去重（v2.2）**：
- ByteTrack为每个目标分配track_id
- TrackManager只在目标离开画面后输出最优检测
- 从源头减少90%+重复

**第2层 - 后处理空间去重（v2.1）**：
- 距离<5米的检测归为同一目标
- 综合评分选择最佳检测
- 跨track_id的近距离重复再清理

**配置控制**：

```yaml
# config/offline_config.yaml
output:
  enable_deduplication: true       # 开启/关闭后处理去重
  deduplication:
    distance_threshold: 5.0        # 距离阈值（米）
    prefer_non_edge: true          # 优先保留画面中央检测
    prefer_high_confidence: true   # 优先保留高置信度
    prefer_rtk: true               # 优先保留RTK定位
    min_quality_score: 0.3         # 最低质量阈值
    edge_penalty: 0.5              # 边缘检测惩罚系数
```

### 统计摘要

运行检测后自动生成 `data/output/summary.txt`，内容包括：

- 检测数量统计（原始、去重后）
- 按类别统计（数量、占比）
- 置信度统计（平均、最高、最低、中位数）
- 地理坐标范围（纬度、经度、高度、覆盖面积）
- GPS质量统计（RTK/HIGH/MEDIUM/LOW分布）
- 边缘检测统计

### 检测截图

**保存位置**：`data/output/images/`

**文件命名**：

```
frame_帧号_obj_序号_类别名_时间戳.jpg

示例：
frame_000123_obj_001_Vegetation_20260210_103015_456.jpg
```

---

## 验证流程

### 推荐流程（v2.1+自动化）

检测完成后**已自动生成**GeoJSON和地图，可以直接：

**步骤1：查看可视化地图**

```bash
# 双击打开自动生成的地图
start data/output/map.html
```

**步骤2：在GIS软件中验证**

```bash
# 在QGIS中打开
# 图层 → 添加图层 → 矢量图层 → 选择：
data/output/geojson/detections_unique.geojson
```

**步骤3：查看统计摘要**

```bash
notepad data/output/summary.txt
```

### 手动验证工具（可选）

```bash
# 手动导出GeoJSON（自定义参数）
python tools/export_to_geojson.py data/output/csv/detections_offline.csv --min-confidence 0.5

# 坐标准确度验证
python tools/sample_validation.py --samples 20 --csv data/output/csv/detections_offline.csv

# 生成提交报告
python tools/generate_report.py --csv data/output/csv/detections_offline.csv
```

### 功能测试（Windows）

```bash
# v2.1功能一键测试
test_v2.1_features.bat
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
# 或手动下载: https://ffmpeg.org/download.html 并添加到PATH

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
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 验证
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### 问题3：坐标偏差很大

**症状**：检测框位置偏移>100米

**排查步骤**：

1. **检查相机参数**：确认 `config/camera_params.yaml` 中的参数与实际相机一致
2. **检查高度数据**：确认SRT/OSD中的altitude字段正确
3. **查看时间同步**：检查日志中的时间差是否<100ms
4. **启用增强版**：设置 `use_enhanced: true` 提高精度
5. **测试样本**：使用已知地标验证转换算法

### 问题4：检测不到目标

**症状**：CSV文件为空或检测数量为0

**排查清单**：

- [ ] 模型文件存在：`models/yolov11x.pt`
- [ ] 置信度阈值：`yolo_config.yaml` 中 `confidence_threshold` 不要太高
- [ ] 目标类别未过滤：`target_classes: null`
- [ ] 图像尺寸合适：`imgsz: 1280`
- [ ] 如果启用跟踪，检查 `min_track_frames` 是否太大

**测试方法**：

```bash
python -c "from ultralytics import YOLO; model = YOLO('models/yolov11x.pt'); model.predict('test.jpg', save=True)"
```

### 问题5：CSV写入失败

**症状**：

```
PermissionError: [Errno 13] Permission denied
```

**解决方案**：

1. 关闭Excel或其他正在打开CSV文件的软件
2. 检查文件夹权限
3. 删除旧的CSV文件

### 问题6：实时模式连接失败

**症状**：

```
[ERROR] Failed to connect to MQTT broker
[ERROR] RTSP stream timeout
```

**排查清单**：

- [ ] 网络连接正常
- [ ] 无人机已开机并连接
- [ ] RTSP地址正确
- [ ] 如果使用HTTP OSD：检查base_url和dev_sn
- [ ] 如果使用MQTT：检查broker、username、password、SN号
- [ ] 防火墙未阻止连接

**测试方法**：

```bash
# 测试HTTP OSD接口
python tools/test_http_osd.py

# 测试RTSP流
ffplay rtsp://192.168.1.100:8554/live

# 测试MQTT连接
mosquitto_sub -h mqtt-cn.dji.com -p 1883 -u username -P password -t test
```

### 问题7：跟踪去重不生效

**症状**：输出中仍有大量重复检测

**排查**：

1. 确认 `yolo_config.yaml` 中 `tracking.enabled: true`
2. 检查 `lost_threshold` 是否合适（太小会提前输出）
3. 检查日志中是否有 `TrackManager` 相关输出
4. 确认模型支持跟踪（某些自定义模型可能不兼容）

---

## 项目交接清单

### 文件交付

- [ ] **源代码**：`src/` 目录完整
  - [ ] `input/` - 8个输入模块（含HTTP OSD客户端）
  - [ ] `detection/` - YOLO检测器 + TrackManager跟踪管理器
  - [ ] `transform/` - 简化版 + 增强版坐标转换器
  - [ ] `output/` - 7个输出模块（含GeoJSON、地图、去重、后处理）
  - [ ] `utils/` - 4个工具模块
  - [ ] 2个管线入口（offline_pipeline.py, realtime_pipeline.py）
- [ ] **配置文件**：`config/` 目录（9个YAML配置）
- [ ] **模型文件**：`models/yolov11x.pt`
- [ ] **依赖列表**：`requirements.txt`
- [ ] **辅助工具**：`tools/` 目录（8个工具脚本）
- [ ] **文档**：
  - [ ] `README.md` - 项目主文档
  - [ ] `README_VIDEO.md` - 视频处理详细文档
  - [ ] `docs/` - 4个专题文档（MQTT配置、HTTP OSD、SOP方案、训练指南）
  - [ ] 根目录中文文档 - v2.0/v2.1/v2.2技术文档和使用指南
  - [ ] `CHANGELOG_v2.1.md` - 版本更新日志
- [ ] **测试文件**：`tests/` 目录 + 根目录测试脚本
- [ ] **快捷脚本**：`run_offline.py`, `run_realtime.py`, `check_before_run.py`
- [ ] **示例数据**（可选）：样例视频和处理结果

### 知识转移要点

**必须讲解的内容**：

1. ✅ 两种工作模式的选择（何时用视频，何时用实时流）
2. ✅ 三种OSD数据源的配置（HTTP/MQTT/auto）
3. ✅ 相机参数的重要性及调整方法
4. ✅ 坐标转换原理（简化版 vs 增强版）
5. ✅ ByteTrack跟踪去重机制
6. ✅ 常见故障排查流程
7. ✅ 配置文件各参数的含义

### 环境配置文档

```
操作系统：Windows 11
Python版本：3.9.x
CUDA版本：12.1
GPU型号：NVIDIA GPU（推荐6GB+显存）
Conda环境名：drone_inspection
关键依赖版本：
  - ultralytics: >=8.3.0
  - opencv-python: >=4.8.0
  - paho-mqtt: >=1.6.1,<2.0.0
  - pyproj: >=3.6.0
  - paddleocr: >=2.7.0
  - paddlepaddle: >=2.6.0,<=3.2.2
  - loguru: >=0.7.0
```

### 技术支持

**联系方式**：

- 项目负责人：[请填写姓名]
- 联系邮箱：[请填写邮箱]
- 技术文档：本README.md + docs/目录

**已知限制**：

- 相机参数需要根据实际设备调整
- 简化版转换器在姿态倾斜时精度下降（建议使用增强版）
- 增强版转换器需要完整的pitch/yaw/roll姿态数据
- 实时模式需要稳定的网络连接
- ByteTrack跟踪在目标快速穿越画面时可能分配多个track_id
- 后处理去重对>10k条记录耗时较长
- HTML地图需要网络加载Leaflet.js和OSM底图

---

## 许可证

本项目仅供学习和研究使用。

---

**开发团队**: Drone Inspection Team
**版本**: v2.2.0
**最后更新**: 2026-02-26

**版本历史**：

| 版本 | 日期 | 主要更新 |
|------|------|---------|
| v2.2.0 | 2026-02-26 | ✅ ByteTrack推理阶段跟踪去重（延迟保存策略）<br/>✅ TrackManager质量评分与缓冲管理<br/>✅ 双重去重机制（推理阶段+后处理阶段） |
| v2.1.0 | 2026-02-25 | ✅ 智能去重（数据量减少70-97%）<br/>✅ GeoJSON自动导出（3个版本）<br/>✅ HTML地图自动生成（Leaflet.js）<br/>✅ 统计摘要自动生成 |
| v2.0.0 | 2026-02-20 | ✅ 增强版坐标转换（3D姿态修正）<br/>✅ GPS质量控制与RTK识别<br/>✅ 定位误差估算 |
| v1.0.0 | 2026-02-15 | ✅ 基础检测功能<br/>✅ 简化版坐标转换<br/>✅ CSV和截图输出 |
