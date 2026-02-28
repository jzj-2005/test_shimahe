"""
YOLOv11-OBB 模型评估脚本
在验证集/测试集上评估 OBB 模型性能，输出 mAP、混淆矩阵、PR 曲线等。

使用方式:
    python tools/evaluate_model.py --model runs/obb/train/weights/best.pt --data data/dataset.yaml
    python tools/evaluate_model.py --model runs/obb/train/weights/best.pt --data data/dataset.yaml --split test
    python tools/evaluate_model.py --model runs/obb/train/weights/best.pt --data data/dataset.yaml --visualize
"""

import argparse
import sys
from pathlib import Path

from ultralytics import YOLO


def evaluate(
    model_path: str,
    data_path: str,
    split: str = "val",
    imgsz: int = 1280,
    batch: int = 8,
    conf: float = 0.001,
    iou: float = 0.7,
    visualize: bool = False,
    device: str = "0",
):
    """运行 OBB 模型评估"""
    if not Path(model_path).exists():
        print(f"[错误] 模型文件不存在: {model_path}")
        sys.exit(1)
    if not Path(data_path).exists():
        print(f"[错误] 数据集配置不存在: {data_path}")
        sys.exit(1)

    print(f"[信息] 加载模型: {model_path}")
    model = YOLO(model_path)

    print(f"[信息] 开始 OBB 评估 (split={split})...")
    val_args = dict(
        data=data_path,
        split=split,
        imgsz=imgsz,
        batch=batch,
        conf=conf,
        iou=iou,
        device=device,
        plots=True,
        save_json=False,
    )

    results = model.val(**val_args)

    print("\n" + "=" * 60)
    print("OBB 评估结果")
    print("=" * 60)

    box = results.box
    print(f"  mAP@0.5:      {box.map50:.4f}")
    print(f"  mAP@0.5:0.95: {box.map:.4f}")

    if hasattr(box, "mp") and hasattr(box, "mr"):
        print(f"  Precision:     {box.mp:.4f}")
        print(f"  Recall:        {box.mr:.4f}")

    if hasattr(box, "ap_class_index") and hasattr(results, "names"):
        print("\n  各类别 mAP@0.5:")
        for i, cls_idx in enumerate(box.ap_class_index):
            cls_name = results.names.get(int(cls_idx), f"class_{cls_idx}")
            ap50 = box.ap50[i] if hasattr(box, "ap50") else 0
            print(f"    {cls_name}: {ap50:.4f}")

    print(f"\n  评估输出目录: {results.save_dir}")
    print("=" * 60)

    if visualize:
        _run_visual_inference(model, data_path, split, imgsz, conf, device)

    return results


def _run_visual_inference(model, data_path, split, imgsz, conf, device):
    """对验证集样本运行推理并保存可视化结果"""
    import yaml

    with open(data_path, "r", encoding="utf-8") as f:
        data_cfg = yaml.safe_load(f)

    base_path = Path(data_path).parent / data_cfg.get("path", ".")
    split_dir = data_cfg.get(split, f"images/{split}")
    images_dir = base_path / split_dir

    if not images_dir.exists():
        print(f"[警告] 图片目录不存在，跳过可视化: {images_dir}")
        return

    image_files = sorted(images_dir.glob("*.jpg")) + sorted(images_dir.glob("*.png"))
    sample_count = min(20, len(image_files))

    if sample_count == 0:
        print("[警告] 未找到图片文件，跳过可视化")
        return

    print(f"\n[信息] 对 {sample_count} 张样本运行可视化推理...")
    sample_images = [str(f) for f in image_files[:sample_count]]

    model.predict(
        source=sample_images,
        imgsz=imgsz,
        conf=conf,
        device=device,
        save=True,
        project="runs/obb",
        name="visualize",
        exist_ok=True,
    )
    print(f"[完成] 可视化结果已保存至 runs/obb/visualize/")


def main():
    parser = argparse.ArgumentParser(description="YOLOv11-OBB 模型评估")
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="OBB 模型权重路径 (如 runs/obb/train/weights/best.pt)",
    )
    parser.add_argument(
        "--data",
        type=str,
        default="data/dataset.yaml",
        help="数据集配置文件路径 (默认: data/dataset.yaml)",
    )
    parser.add_argument(
        "--split",
        type=str,
        choices=["val", "test"],
        default="val",
        help="评估数据集划分 (默认: val)",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=1280,
        help="图像尺寸 (默认: 1280)",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=8,
        help="批大小 (默认: 8)",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.001,
        help="置信度阈值 (默认: 0.001, 评估时通常设低)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="0",
        help="设备 (默认: 0, 即第一块 GPU)",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="是否对样本运行推理并保存可视化结果",
    )
    args = parser.parse_args()

    evaluate(
        model_path=args.model,
        data_path=args.data,
        split=args.split,
        imgsz=args.imgsz,
        batch=args.batch,
        conf=args.conf,
        visualize=args.visualize,
        device=args.device,
    )


if __name__ == "__main__":
    main()
