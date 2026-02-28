# YOLOv11-OBB 旋转框检测模型训练指南

本指南涵盖从数据准备到模型部署的完整 OBB（Oriented Bounding Box）训练流程，适用于河湖"四乱"航拍场景下的倾斜目标检测。

---

## 目录

1. [为什么选择 OBB](#1-为什么选择-obb)
2. [环境准备](#2-环境准备)
3. [数据准备](#3-数据准备)
4. [旋转框标注规范](#4-旋转框标注规范)
5. [训练参数与流程](#5-训练参数与流程)
6. [模型评估](#6-模型评估)
7. [部署到检测系统](#7-部署到检测系统)
8. [常见问题排查](#8-常见问题排查)

---

## 1. 为什么选择 OBB

传统水平框（HBB）在航拍倾斜建筑场景下存在以下问题：

- **检测框过大**：水平框包含大量背景区域，无法精确贴合倾斜目标
- **密集目标重叠**：相邻建筑的水平框容易互相重叠，NMS 误删真正目标
- **定位不准**：无法反映目标的真实朝向和轮廓

OBB 旋转框可以紧密贴合目标的实际轮廓，从根本上解决这些问题。

## 2. 环境准备

### 硬件要求

| 项目 | 最低配置 | 推荐配置 |
|------|---------|---------|
| GPU | NVIDIA GTX 1080 Ti (11GB) | NVIDIA RTX 3090/4090 (24GB) |
| 内存 | 16 GB | 32 GB |
| 硬盘 | 50 GB 可用空间 | 100 GB SSD |

### 软件依赖

```bash
# 确保 Python >= 3.8
python --version

# 安装/升级 ultralytics（需要 >= 8.1.0 以获得 OBB 支持）
pip install ultralytics>=8.1.0

# 验证 GPU 可用
python -c "import torch; print(torch.cuda.is_available())"
```

### 下载预训练模型

```bash
# yolo11x-obb.pt 基于 DOTA 数据集预训练，已具备旋转框检测能力
yolo obb detect model=yolo11x-obb.pt source=test.jpg
```

首次运行时会自动下载预训练权重。也可以手动从 [Ultralytics 官方](https://docs.ultralytics.com/models/) 下载。

## 3. 数据准备

### 3.1 从巡检视频提取帧

使用项目自带的帧提取工具：

```bash
python tools/extract_training_frames.py \
    --video data/videos/inspection_01.mp4 \
    --output data/training/images \
    --interval 30 \
    --format yolo_obb
```

参数说明：
- `--interval 30`：每隔 30 帧提取一张（约 1 秒一帧，适合 30fps 视频）
- `--format yolo_obb`：自动创建 YOLO OBB 数据集目录结构

### 3.2 推荐数据量

| 类别 | 最低标注量 | 推荐标注量 | 说明 |
|------|-----------|-----------|------|
| 每个类别 | 200 张 | 500-1000 张 | 越多越好，注意类别平衡 |
| 总数据量 | 1000 张 | 3000-5000 张 | 包含多样化场景 |

### 3.3 数据集目录结构

```
data/training/
├── images/
│   ├── train/          # 训练集图片（70%）
│   │   ├── img_0001.jpg
│   │   ├── img_0002.jpg
│   │   └── ...
│   ├── val/            # 验证集图片（20%）
│   │   └── ...
│   └── test/           # 测试集图片（10%）
│       └── ...
├── labels/
│   ├── train/          # 训练集标签（与图片一一对应）
│   │   ├── img_0001.txt
│   │   ├── img_0002.txt
│   │   └── ...
│   ├── val/
│   │   └── ...
│   └── test/
│       └── ...
└── dataset.yaml        # 数据集配置文件
```

> **重要**：labels 目录下的 txt 文件名必须与 images 目录下的图片文件名（不含扩展名）完全一致。

### 3.4 数据集划分

推荐比例 **train : val : test = 7 : 2 : 1**

- **训练集**：用于模型学习
- **验证集**：用于训练过程中监控指标，选择最优模型
- **测试集**：训练完成后独立评估模型泛化能力

打乱数据后按比例分配，确保每个类别在三个子集中分布均匀。

## 4. 旋转框标注规范

### 4.1 标注工具推荐

| 工具 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **CVAT** | 免费开源、原生支持旋转框、可本地部署 | 界面较复杂 | ★★★★★ |
| **Roboflow** | 可视化好、支持导出 YOLO-OBB 格式、在线协作 | 免费版有限额 | ★★★★☆ |
| **Label Studio** | 功能全面、支持旋转框 | 配置较复杂 | ★★★☆☆ |

**推荐使用 CVAT**（免费，原生旋转框支持最好）。

### 4.2 YOLO OBB 标签格式

每张图片对应一个 `.txt` 标签文件，每行一个目标：

```
class_id x1 y1 x2 y2 x3 y3 x4 y4
```

- `class_id`：类别索引（从 0 开始的整数）
- `x1 y1 ... x4 y4`：旋转框四个角点坐标，**归一化到 [0, 1]**（相对于图片宽高）

示例（一张图片中有两个目标）：

```
0 0.532 0.318 0.695 0.289 0.712 0.456 0.549 0.485
3 0.215 0.612 0.398 0.583 0.415 0.750 0.232 0.779
```

### 4.3 坐标归一化方法

```
x_normalized = x_pixel / image_width
y_normalized = y_pixel / image_height
```

### 4.4 标注原则

1. **紧密贴合**：旋转框应紧密贴合目标（如建筑屋顶）的实际轮廓，尽量不包含背景
2. **按实际朝向**：框的朝向应与目标实际朝向一致，充分利用旋转框优势
3. **逐个标注**：密集建筑群中的每个建筑单独标注，不要合并
4. **合理推断**：被部分遮挡的目标，按合理推断补全旋转框
5. **角点顺序**：四个角点按顺时针或逆时针连续排列
6. **一致性**：同一类别的标注标准保持一致

### 4.5 各类别标注要点

| 类别 | 标注重点 | 注意事项 |
|------|---------|---------|
| 乱占 (违规占用河道) | 框选占用区域的完整范围 | 与河道边界对齐 |
| 乱采 (非法采砂/采矿) | 框选采砂场/矿坑轮廓 | 注意区分正常水面 |
| 乱堆 (违规堆放) | 框选堆放物的外轮廓 | 包含堆体的完整阴影区域 |
| 乱建 (违法建筑) | 紧密贴合建筑屋顶轮廓 | 按建筑实际朝向旋转 |

### 4.6 从 CVAT 导出 YOLO OBB 格式

1. 在 CVAT 中完成标注
2. 点击 **Menu → Export task dataset**
3. 选择格式：**YOLO OBB 1.0**
4. 下载并解压到 `data/training/` 目录
5. 检查标签文件格式是否正确（每行 9 个数值）

## 5. 训练参数与流程

### 5.1 配置文件

训练前需要准备两个配置文件：

**数据集配置** `data/dataset.yaml`：

```yaml
path: ../data/training
train: images/train
val: images/val
test: images/test
names:
  0: "乱占"
  1: "乱采"
  2: "乱堆"
  3: "乱建"
```

**训练参数配置** `config/training_config.yaml`：

```yaml
task: obb
model: yolo11x-obb.pt
data: data/dataset.yaml
epochs: 150
imgsz: 1280
batch: 8
```

### 5.2 使用训练脚本

```bash
# 基本训练
python tools/train_model.py

# 指定配置文件
python tools/train_model.py --config config/training_config.yaml

# 断点续训
python tools/train_model.py --resume runs/obb/train/weights/last.pt
```

### 5.3 核心训练参数说明

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `task` | `obb` | 旋转框检测任务（非 `detect`） |
| `model` | `yolo11x-obb.pt` | DOTA 预训练的 OBB 模型 |
| `epochs` | 150 | 训练轮数，可根据验证集 loss 调整 |
| `imgsz` | 1280 | 输入图像尺寸，航拍场景建议 ≥ 1280 |
| `batch` | 8 | 批大小，根据 GPU 显存调整（24GB → 8, 11GB → 4） |
| `lr0` | 0.01 | 初始学习率 |
| `lrf` | 0.01 | 最终学习率系数（lr_final = lr0 × lrf） |
| `optimizer` | `SGD` | 优化器 |
| `degrees` | 180.0 | 旋转增强角度范围，对 OBB 特别重要 |
| `flipud` | 0.5 | 上下翻转概率 |
| `fliplr` | 0.5 | 左右翻转概率 |
| `mosaic` | 1.0 | Mosaic 增强概率 |
| `patience` | 30 | 早停轮数（验证指标无改善则停止） |

### 5.4 数据增强建议

OBB 训练中旋转增强尤为重要：

```yaml
# 在训练配置中设置
degrees: 180.0    # 旋转范围 [-180, 180]，OBB 任务必须设大
flipud: 0.5       # 上下翻转
fliplr: 0.5       # 左右翻转
mosaic: 1.0       # Mosaic 增强
mixup: 0.1        # MixUp 增强
```

### 5.5 训练过程监控

训练过程中观察以下指标：

- **train/box_loss**：旋转框回归损失，应持续下降
- **train/cls_loss**：分类损失，应持续下降
- **val/mAP50(OBB)**：验证集 OBB IoU@0.5 的 mAP，核心指标
- **val/mAP50-95(OBB)**：更严格的评估指标

使用 TensorBoard 查看训练曲线：

```bash
tensorboard --logdir runs/obb/train
```

## 6. 模型评估

### 6.1 使用评估脚本

```bash
# 在验证集上评估
python tools/evaluate_model.py \
    --model runs/obb/train/weights/best.pt \
    --data data/dataset.yaml

# 在测试集上评估（最终评估）
python tools/evaluate_model.py \
    --model runs/obb/train/weights/best.pt \
    --data data/dataset.yaml \
    --split test

# 可视化检测结果
python tools/evaluate_model.py \
    --model runs/obb/train/weights/best.pt \
    --data data/dataset.yaml \
    --visualize
```

### 6.2 评估指标

| 指标 | 含义 | 目标值 |
|------|------|--------|
| mAP@0.5 (OBB) | OBB IoU ≥ 0.5 时的平均精度 | ≥ 0.7 |
| mAP@0.5:0.95 (OBB) | 多阈值平均精度 | ≥ 0.5 |
| Precision | 检测结果中正确的比例 | ≥ 0.8 |
| Recall | 实际目标被检测出的比例 | ≥ 0.7 |

### 6.3 评估输出文件

评估脚本会在 `runs/obb/val/` 目录下生成：

- `confusion_matrix.png`：混淆矩阵
- `PR_curve.png`：Precision-Recall 曲线
- `F1_curve.png`：F1 曲线
- `results.csv`：详细数值结果
- `val_batch*_pred.jpg`：可视化预测结果

## 7. 部署到检测系统

### 7.1 替换模型文件

将训练好的最优模型复制到项目 models 目录：

```bash
cp runs/obb/train/weights/best.pt models/best_obb.pt
```

### 7.2 修改配置文件

编辑 `config/yolo_config.yaml`：

```yaml
model:
  path: "./models/best_obb.pt"    # 指向 OBB 模型
  type: "yolo11x-obb"             # 模型类型
  obb_mode: true                  # 启用 OBB 旋转框模式

classes:
  names:
    0: "乱占"
    1: "乱采"
    2: "乱堆"
    3: "乱建"
```

### 7.3 验证部署

```bash
# 用离线模式测试一段视频
python main.py --config config/offline_config.yaml --video test_video.mp4
```

检查输出的检测图像是否正确绘制了旋转框。

### 7.4 回退到 HBB 模式

如需回退，只需将 `obb_mode` 设为 `false`：

```yaml
model:
  path: "./models/yolov11x.pt"
  type: "yolov11x"
  obb_mode: false
```

系统会自动切换回水平框检测逻辑，完全兼容。

## 8. 常见问题排查

### Q: 训练时报 "No labels found" 错误

检查标签文件路径和格式：
- 标签文件必须在 `labels/` 目录下（与 `images/` 同级）
- 文件名必须与图片一一对应
- 每行格式：`class_id x1 y1 x2 y2 x3 y3 x4 y4`（9 个数值）

### Q: 训练 loss 不下降

- 检查标注质量，确保旋转框标注正确
- 降低初始学习率 `lr0`
- 增加训练数据量
- 确认 `task: obb` 而非 `task: detect`

### Q: GPU 显存不足（OOM）

- 减小 `batch` 大小（如 8 → 4 → 2）
- 减小 `imgsz`（如 1280 → 640）
- 使用较小模型（如 `yolo11s-obb.pt`）

### Q: mAP 较低

- 增加训练数据和标注质量
- 增大 `degrees` 旋转增强范围
- 增加训练 `epochs`
- 尝试更大的 `imgsz`
- 检查类别不平衡问题，考虑过采样

### Q: OBB 模式下跟踪失效

- `model.track()` 同样支持 OBB 模型，确保 tracker 配置正确
- 如果 track_id 不稳定，尝试调整 ByteTrack 参数

### Q: 旋转框检测结果方向不对

- 检查标注时角点顺序是否一致
- 确保使用了 `yolo11x-obb.pt` 预训练模型而非普通 `yolo11x.pt`
