"""
从巡检视频中按帧间隔提取图片，用于模型训练数据准备。
自动创建 YOLO OBB 数据集目录结构。

使用方式:
    python tools/extract_training_frames.py --video data/videos/demo.mp4 --output data/training/images --interval 30
    python tools/extract_training_frames.py --video data/videos/ --output data/training/images --interval 30
"""

import argparse
import os
import sys
from pathlib import Path

import cv2


def create_dataset_structure(base_dir: str):
    """创建 YOLO OBB 数据集目录结构"""
    dirs = [
        os.path.join(base_dir, "images", "train"),
        os.path.join(base_dir, "images", "val"),
        os.path.join(base_dir, "images", "test"),
        os.path.join(base_dir, "labels", "train"),
        os.path.join(base_dir, "labels", "val"),
        os.path.join(base_dir, "labels", "test"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    print(f"[信息] 数据集目录结构已创建: {base_dir}")
    for d in dirs:
        print(f"  {d}")


def extract_frames_from_video(
    video_path: str,
    output_dir: str,
    interval: int = 30,
    max_frames: int = 0,
    prefix: str = "",
) -> int:
    """
    从单个视频中按帧间隔提取图片。

    Returns:
        提取的帧数
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[错误] 无法打开视频: {video_path}")
        return 0

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    video_name = Path(video_path).stem

    if not prefix:
        prefix = video_name

    print(f"[信息] 处理视频: {video_path}")
    print(f"  总帧数: {total_frames}, FPS: {fps:.1f}, 提取间隔: {interval} 帧")

    os.makedirs(output_dir, exist_ok=True)

    frame_idx = 0
    saved_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % interval == 0:
            filename = f"{prefix}_frame_{frame_idx:06d}.jpg"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            saved_count += 1

            if saved_count % 50 == 0:
                print(f"  已提取 {saved_count} 帧...")

            if max_frames > 0 and saved_count >= max_frames:
                break

        frame_idx += 1

    cap.release()
    print(f"  完成: 提取 {saved_count} 帧 → {output_dir}")
    return saved_count


def main():
    parser = argparse.ArgumentParser(
        description="从巡检视频提取训练图片，支持自动创建 YOLO OBB 数据集目录"
    )
    parser.add_argument(
        "--video",
        type=str,
        required=True,
        help="视频文件路径或包含视频的目录",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="图片输出目录",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="帧提取间隔（每隔 N 帧提取一张，默认 30）",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="每个视频最大提取帧数（0 = 不限制）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["flat", "yolo_obb"],
        default="flat",
        help="输出格式: flat=所有帧输出到同一目录, yolo_obb=创建 YOLO OBB 数据集目录结构",
    )
    args = parser.parse_args()

    video_path = Path(args.video)
    video_extensions = {".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv"}

    if args.format == "yolo_obb":
        base_dir = str(Path(args.output).parent.parent)
        create_dataset_structure(base_dir)
        print("[提示] 提取的帧将输出到指定目录，标注后请手动划分到 train/val/test 子目录")

    total_saved = 0

    if video_path.is_file():
        total_saved = extract_frames_from_video(
            str(video_path), args.output, args.interval, args.max_frames
        )
    elif video_path.is_dir():
        video_files = sorted(
            f for f in video_path.iterdir() if f.suffix.lower() in video_extensions
        )
        if not video_files:
            print(f"[错误] 目录中未找到视频文件: {video_path}")
            sys.exit(1)
        print(f"[信息] 找到 {len(video_files)} 个视频文件")
        for vf in video_files:
            count = extract_frames_from_video(
                str(vf), args.output, args.interval, args.max_frames
            )
            total_saved += count
    else:
        print(f"[错误] 路径不存在: {video_path}")
        sys.exit(1)

    print(f"\n[完成] 共提取 {total_saved} 帧图片 → {args.output}")
    if args.format == "yolo_obb":
        print("[下一步] 使用标注工具（CVAT / Roboflow）对图片进行旋转框标注")


if __name__ == "__main__":
    main()
