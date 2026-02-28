"""
YOLOv11-OBB 旋转框模型训练脚本
封装 ultralytics YOLO OBB 训练 API，支持从配置文件读取参数和断点续训。

使用方式:
    python tools/train_model.py
    python tools/train_model.py --config config/training_config.yaml
    python tools/train_model.py --resume runs/obb/train/weights/last.pt
"""

import argparse
import sys
from pathlib import Path

import yaml
from ultralytics import YOLO


DEFAULT_CONFIG = "config/training_config.yaml"


def load_config(config_path: str) -> dict:
    """加载 YAML 训练配置文件"""
    path = Path(config_path)
    if not path.exists():
        print(f"[错误] 配置文件不存在: {config_path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    print(f"[信息] 已加载训练配置: {config_path}")
    return config


def train(config: dict):
    """执行 OBB 训练"""
    model_name = config.pop("model", "yolo11x-obb.pt")
    task = config.pop("task", "obb")

    if task != "obb":
        print(f"[警告] task={task}，OBB 训练应使用 task=obb，已自动修正")
        task = "obb"

    print(f"[信息] 加载预训练模型: {model_name}")
    model = YOLO(model_name)

    train_args = {k: v for k, v in config.items() if v is not None}

    print("[信息] 开始 OBB 训练...")
    print(f"  数据集: {train_args.get('data', 'N/A')}")
    print(f"  轮数:   {train_args.get('epochs', 'N/A')}")
    print(f"  图像尺寸: {train_args.get('imgsz', 'N/A')}")
    print(f"  批大小: {train_args.get('batch', 'N/A')}")

    results = model.train(**train_args)

    best_path = Path(results.save_dir) / "weights" / "best.pt"
    print("\n" + "=" * 60)
    print("[完成] 训练结束！")
    print(f"  最优模型: {best_path}")
    print(f"  训练输出: {results.save_dir}")
    print("=" * 60)

    return results


def resume_training(checkpoint_path: str):
    """从检查点断点续训"""
    path = Path(checkpoint_path)
    if not path.exists():
        print(f"[错误] 检查点文件不存在: {checkpoint_path}")
        sys.exit(1)

    print(f"[信息] 从检查点恢复训练: {checkpoint_path}")
    model = YOLO(checkpoint_path)
    results = model.train(resume=True)

    best_path = Path(results.save_dir) / "weights" / "best.pt"
    print("\n" + "=" * 60)
    print("[完成] 续训结束！")
    print(f"  最优模型: {best_path}")
    print(f"  训练输出: {results.save_dir}")
    print("=" * 60)

    return results


def main():
    parser = argparse.ArgumentParser(description="YOLOv11-OBB 旋转框模型训练")
    parser.add_argument(
        "--config",
        type=str,
        default=DEFAULT_CONFIG,
        help=f"训练配置文件路径 (默认: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="断点续训的检查点路径 (如 runs/obb/train/weights/last.pt)",
    )
    args = parser.parse_args()

    if args.resume:
        resume_training(args.resume)
    else:
        config = load_config(args.config)
        train(config)


if __name__ == "__main__":
    main()
