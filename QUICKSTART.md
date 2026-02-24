# 视频推理环境准备完成清单

## 已完成准备工作

### 1. 环境检查 ✓

- **GPU**: RTX 3050 6GB (可用)
- **Python环境**: yolo11m-orthophoto (已激活)
- **必需库**: pandas已安装
- **FFmpeg**: ⚠️ 需要安装 (见下方说明)

### 2. 工具创建 ✓

所有验证工具已创建并测试通过:

- `tools/export_to_geojson.py` - GeoJSON导出工具
- `tools/quick_visualize.py` - 交互式地图生成
- `tools/generate_report.py` - 报告生成工具
- `tools/sample_validation.py` - 坐标验证工具

### 3. 快捷脚本 ✓

- `run_video.bat` - 视频推理快捷启动
- `run_validation.bat` - 完整验证流程
- `install_ffmpeg.bat` - FFmpeg安装脚本

### 4. 文档 ✓

- `README_VIDEO.md` - 完整使用指南（详细版）
- `QUICKSTART.md` - 本文件（快速开始）

---

## ⚠️ 下午处理视频前必须做的事

### 安装FFmpeg（5分钟）

**方法1: 使用安装脚本（推荐）**

```bash
.\install_ffmpeg.bat
```

**方法2: 手动安装**

1. 下载FFmpeg: https://ffmpeg.org/download.html (选择Windows版本)
2. 解压到 `C:\ffmpeg`
3. 添加环境变量: `C:\ffmpeg\bin` 添加到系统PATH
4. 验证: 打开新终端运行 `ffmpeg -version`

---

## 🚀 下午拿到视频后的操作流程

### 快速流程（推荐）

```bash
# 1. 将视频放入指定目录
复制视频到: d:\jzj\siluan_new\data\input\videos\

# 2. 双击运行
run_video.bat

# 3. 在弹出的输入框中输入视频路径，或直接拖拽视频到终端

# 4. 等待处理完成（10-20分钟）

# 5. 双击运行验证流程
run_validation.bat

# 按提示完成所有步骤，最后会生成提交报告
```

### 手动流程（详细控制）

```bash
# 步骤1: 激活环境
conda activate yolo11m-orthophoto

# 步骤2: 运行视频推理
python run_offline.py "data/input/videos/DJI_0001.MP4"

# 步骤3: 导出GeoJSON
python tools/export_to_geojson.py data/output/csv/detections_offline.csv

# 步骤4: 查看地图
python tools/quick_visualize.py

# 步骤5: 抽样验证（可选，5-10分钟）
python tools/sample_validation.py --samples 20

# 步骤6: 生成报告
python tools/generate_report.py
```

---

## 📦 提交文件清单

处理完成后，打包以下文件提交给公司:

### 必须提交

```
data/output/
├── csv/detections_offline.csv          # CSV检测结果
├── detections.geojson                   # GeoJSON可视化数据
├── map.html                             # 交互式地图
└── delivery_report.md                   # 检测报告
```

### 可选提交

```
data/output/
├── detections_high_conf.geojson        # 高置信度检测
├── summary.txt                          # 统计摘要
├── validation_results_*.json            # 验证结果（如果完成）
└── images/                              # 检测目标截图（选择性）
```

---

## ⏱️ 预计时间安排

| 任务 | 预计时间 |
|-----|---------|
| 安装FFmpeg | 5分钟 |
| 视频推理处理 | 10-20分钟 |
| 导出+可视化 | 2分钟 |
| 抽样验证（可选） | 5-10分钟 |
| 生成报告 | 1分钟 |
| **总计** | **20-40分钟** |

---

## 🔧 配置参数（可选调整）

如果处理速度太慢，可以修改 `config/offline_config.yaml`:

```yaml
video_processing:
  frame_skip: 2  # 改为3可以更快但会跳过更多帧

detection:
  imgsz: 1280    # 改为640可以更快但精度略降
```

---

## ❓ 常见问题快速解决

### 问题1: 提示"无法找到FFmpeg"
**解决**: 运行 `install_ffmpeg.bat` 或手动安装

### 问题2: GPU内存不足
**解决**: 修改 `config/yolo_config.yaml`，将 `imgsz: 1280` 改为 `640`

### 问题3: 找不到SRT文件
**解决**: 确保SRT与视频同名同目录，或手动指定:
```bash
python run_offline.py "视频.MP4" --srt "字幕.srt"
```

### 问题4: 处理速度慢
**解决**: 增加跳帧 `frame_skip: 2` 改为 `frame_skip: 3`

---

## 📞 技术支持

如遇到问题，查阅详细文档:
- 完整指南: `README_VIDEO.md`
- 配置说明: 见README第📊节
- 问题排查: 见README第❓节

---

## ✅ 准备就绪！

- [x] 环境已检查
- [x] 工具已创建
- [x] 脚本已准备
- [x] 文档已完成
- [ ] **待办: 安装FFmpeg**

**下午拿到视频后，直接运行 `run_video.bat` 即可！**

---

最后更新: 2026-02-11
版本: v1.0
