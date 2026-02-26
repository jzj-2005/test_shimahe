"""
实时管道模拟验证脚本
在没有真实 MQTT/RTSP 连接的情况下，验证实时处理管道的端到端流程。

用法:
    # 使用本地视频文件
    python test_realtime_simulation.py --video ./data/input/videos/DJI_0001.MP4

    # 不指定视频，自动生成合成帧
    python test_realtime_simulation.py

    # 指定处理帧数和起始GPS坐标
    python test_realtime_simulation.py --video test.mp4 --max-frames 50 --lat 22.78 --lon 114.10

验证范围:
    1. YOLO 检测器（真实模型推理）
    2. 坐标转换器（像素坐标 -> CGCS2000 地理坐标）
    3. 报告生成器（CSV 输出 + 图片保存）
    4. 可视化器（可选，实时显示检测结果）
"""

import sys
import time
import random
import argparse
import numpy as np
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger


def print_banner(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_step(num: int, total: int, desc: str):
    print(f"\n[{num}/{total}] {desc}")
    print("-" * 60)


class PoseSimulator:
    """模拟无人机位姿数据生成器，沿直线飞行轨迹生成 GPS + 姿态数据"""

    def __init__(self, start_lat: float, start_lon: float, altitude: float,
                 speed_mps: float = 5.0):
        self.lat = start_lat
        self.lon = start_lon
        self.altitude = altitude
        self.speed = speed_mps
        self.yaw = random.uniform(0, 360)
        self.frame_idx = 0

        # 飞行方向 (北偏东 yaw 度)
        self.heading_rad = np.radians(self.yaw)
        self.meters_per_deg_lat = 110540.0
        self.meters_per_deg_lon = 111320.0 * np.cos(np.radians(self.lat))

    def next_pose(self, dt: float = 0.1) -> dict:
        """生成下一帧的位姿数据

        Args:
            dt: 与上一帧的时间间隔 (秒)
        """
        distance = self.speed * dt
        dlat = distance * np.cos(self.heading_rad) / self.meters_per_deg_lat
        dlon = distance * np.sin(self.heading_rad) / self.meters_per_deg_lon

        self.lat += dlat
        self.lon += dlon
        # 轻微高度波动
        alt_jitter = random.uniform(-0.3, 0.3)

        pose = {
            'timestamp': time.time() * 1000,
            'latitude': self.lat,
            'longitude': self.lon,
            'altitude': self.altitude + alt_jitter,
            'yaw': self.yaw + random.uniform(-1, 1),
            'pitch': -90.0 + random.uniform(-0.5, 0.5),
            'roll': random.uniform(-0.3, 0.3),
        }
        self.frame_idx += 1
        return pose


def generate_synthetic_frame(width: int = 1920, height: int = 1080) -> np.ndarray:
    """生成带有简单图案的合成帧（用于没有本地视频时测试）"""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    # 绿色地面背景
    frame[:, :] = (34, 85, 34)
    # 随机矩形模拟地物
    for _ in range(random.randint(3, 8)):
        x1 = random.randint(0, width - 200)
        y1 = random.randint(0, height - 200)
        x2 = x1 + random.randint(60, 200)
        y2 = y1 + random.randint(60, 200)
        color = (
            random.randint(80, 220),
            random.randint(80, 220),
            random.randint(80, 220),
        )
        frame[y1:y2, x1:x2] = color
    return frame


def run_simulation(args):
    """运行模拟验证"""
    total_steps = 6
    results = {}

    # ------------------------------------------------------------------
    # Step 1: 加载配置
    # ------------------------------------------------------------------
    print_step(1, total_steps, "加载配置文件")
    try:
        from src.utils.config_loader import ConfigLoader
        config_loader = ConfigLoader(args.config)
        realtime_config = config_loader.load('realtime_config')
        yolo_config = config_loader.load('yolo_config')
        camera_config = config_loader.load('camera_params')
        print("  [OK] 配置文件加载成功")
        print(f"       YOLO 模型: {yolo_config.get('model', {}).get('path')}")
        print(f"       相机型号:  {camera_config.get('camera', {}).get('model')}")
        results['config'] = True
    except Exception as e:
        print(f"  [FAIL] 配置加载失败: {e}")
        results['config'] = False
        return results

    # ------------------------------------------------------------------
    # Step 2: 初始化 YOLO 检测器
    # ------------------------------------------------------------------
    print_step(2, total_steps, "初始化 YOLO 检测器")
    try:
        from src.detection.yolo_detector import YOLODetector
        model_cfg = yolo_config.get('model', {})
        det_cfg = yolo_config.get('detection', {})
        cls_cfg = yolo_config.get('classes', {})

        detector = YOLODetector(
            model_path=model_cfg.get('path', './models/yolov11x.pt'),
            confidence_threshold=det_cfg.get('confidence_threshold', 0.5),
            iou_threshold=det_cfg.get('iou_threshold', 0.45),
            device=model_cfg.get('device', 'cuda'),
            half_precision=model_cfg.get('half_precision', False),
            imgsz=det_cfg.get('imgsz', 640),
            class_names=cls_cfg.get('names', {}),
            target_classes=cls_cfg.get('target_classes'),
        )
        print("  [OK] YOLO 检测器初始化成功")
        results['detector'] = True
    except Exception as e:
        print(f"  [FAIL] YOLO 初始化失败: {e}")
        results['detector'] = False
        return results

    # ------------------------------------------------------------------
    # Step 3: 初始化坐标转换器
    # ------------------------------------------------------------------
    print_step(3, total_steps, "初始化坐标转换器")
    try:
        from src.transform.camera_model import CameraModel

        camera_model = CameraModel(camera_config)
        coord_cfg = camera_config.get('coordinate_transform', {})

        if coord_cfg.get('use_enhanced', False):
            from src.transform.coord_transform_new import CoordinateTransformerEnhanced
            transformer = CoordinateTransformerEnhanced(
                camera_model=camera_model,
                quality_config=coord_cfg.get('quality_control', {}),
            )
            print("  [OK] 增强版坐标转换器初始化成功")
        else:
            from src.transform.coord_transform import CoordinateTransformer
            transformer = CoordinateTransformer(camera_model)
            print("  [OK] 简化版坐标转换器初始化成功")
        results['transformer'] = True
    except Exception as e:
        print(f"  [FAIL] 坐标转换器初始化失败: {e}")
        results['transformer'] = False
        return results

    # ------------------------------------------------------------------
    # Step 4: 初始化报告生成器
    # ------------------------------------------------------------------
    print_step(4, total_steps, "初始化报告生成器")
    try:
        from src.output.report_generator import ReportGenerator
        output_cfg = realtime_config.get('output', {})

        sim_csv = args.output_csv or "./data/output/csv/detections_simulation.csv"
        sim_img = args.output_images or "./data/output/images_simulation/"

        report_gen = ReportGenerator(
            csv_path=sim_csv,
            image_dir=sim_img,
            save_images=output_cfg.get('save_images', True),
            image_format=output_cfg.get('image_format', 'full'),
            image_quality=output_cfg.get('image_quality', 85),
            csv_write_mode='overwrite',
        )
        print(f"  [OK] 报告生成器初始化成功")
        print(f"       CSV 输出: {sim_csv}")
        print(f"       图片目录: {sim_img}")
        results['report_gen'] = True
    except Exception as e:
        print(f"  [FAIL] 报告生成器初始化失败: {e}")
        results['report_gen'] = False
        return results

    # ------------------------------------------------------------------
    # Step 5: 准备视频源 + 位姿模拟器
    # ------------------------------------------------------------------
    print_step(5, total_steps, "准备视频源和位姿模拟器")

    video_reader = None
    use_video_file = False

    if args.video:
        video_path = Path(args.video)
        if video_path.exists():
            from src.input.video_file_reader import VideoFileReader
            video_reader = VideoFileReader(
                video_path=str(video_path),
                frame_skip=args.frame_skip,
            )
            if video_reader.open():
                use_video_file = True
                print(f"  [OK] 视频文件已打开: {video_path}")
                print(f"       分辨率: {video_reader.width}x{video_reader.height}")
                print(f"       帧率: {video_reader.fps:.1f}")
                print(f"       总帧数: {video_reader.frame_count}")
            else:
                print(f"  [WARN] 无法打开视频 {video_path}，将使用合成帧")
        else:
            print(f"  [WARN] 视频文件不存在: {video_path}，将使用合成帧")

    if not use_video_file:
        print("  [INFO] 使用合成帧模式（随机生成图像）")

    pose_sim = PoseSimulator(
        start_lat=args.lat,
        start_lon=args.lon,
        altitude=args.altitude,
        speed_mps=args.speed,
    )
    print(f"  [OK] 位姿模拟器已创建")
    print(f"       起始坐标: ({args.lat:.6f}, {args.lon:.6f})")
    print(f"       飞行高度: {args.altitude}m, 速度: {args.speed}m/s")

    # ------------------------------------------------------------------
    # Step 6: 运行模拟处理循环
    # ------------------------------------------------------------------
    print_step(6, total_steps, "运行模拟处理循环")

    max_frames = args.max_frames
    frame_count = 0
    detection_count = 0
    transform_count = 0
    save_count = 0
    errors = []
    start_time = time.time()

    print(f"  最多处理 {max_frames} 帧...")
    print()

    try:
        while frame_count < max_frames:
            # --- 获取帧 ---
            if use_video_file:
                success, frame, metadata = video_reader.read()
                if not success or frame is None:
                    print(f"  视频读取完毕，共读取 {frame_count} 帧")
                    break
                frame_number = metadata['frame_number']
            else:
                frame = generate_synthetic_frame()
                frame_number = frame_count

            # --- 生成位姿 ---
            dt = 1.0 / 30.0 if not use_video_file else 1.0 / max(video_reader.fps, 1)
            pose = pose_sim.next_pose(dt=dt * (args.frame_skip if use_video_file else 1))

            # --- YOLO 检测 ---
            try:
                detections = detector.detect(frame, check_edge=True)
            except Exception as e:
                errors.append(f"帧{frame_number} 检测失败: {e}")
                frame_count += 1
                continue

            if detections:
                detection_count += len(detections)

                # --- 坐标转换 ---
                try:
                    detections = transformer.transform_detections(detections, pose)
                    transform_count += len(detections)
                except Exception as e:
                    errors.append(f"帧{frame_number} 坐标转换失败: {e}")

                # --- 保存结果 ---
                try:
                    report_gen.save_realtime(detections, frame, pose, frame_number)
                    save_count += len(detections)
                except Exception as e:
                    errors.append(f"帧{frame_number} 保存失败: {e}")

            frame_count += 1

            # 进度输出
            if frame_count % 10 == 0 or frame_count == 1:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                print(f"  帧 {frame_count:>4d}/{max_frames} | "
                      f"检测 {detection_count:>4d} | "
                      f"坐标转换 {transform_count:>4d} | "
                      f"已保存 {save_count:>4d} | "
                      f"{fps:.1f} fps")

    except KeyboardInterrupt:
        print("\n  [INFO] 用户中断")
    except Exception as e:
        print(f"\n  [ERROR] 处理循环异常: {e}")
        import traceback
        traceback.print_exc()
        errors.append(f"处理循环异常: {e}")

    # 清理
    elapsed_total = time.time() - start_time
    if use_video_file and video_reader:
        video_reader.close()

    try:
        report_gen.close()
    except Exception as e:
        logger.warning(f"关闭报告生成器出错: {e}")

    # ------------------------------------------------------------------
    # 结果汇总
    # ------------------------------------------------------------------
    print_banner("模拟验证结果")

    print(f"\n  处理帧数:     {frame_count}")
    print(f"  检测目标数:   {detection_count}")
    print(f"  坐标转换数:   {transform_count}")
    print(f"  保存记录数:   {save_count}")
    print(f"  总耗时:       {elapsed_total:.1f} 秒")
    if frame_count > 0:
        print(f"  平均帧率:     {frame_count / elapsed_total:.1f} fps")

    if errors:
        print(f"\n  运行过程中出现 {len(errors)} 个错误:")
        for err in errors[:5]:
            print(f"    - {err}")
        if len(errors) > 5:
            print(f"    ... 还有 {len(errors) - 5} 个错误")

    # 检查输出文件
    print(f"\n  输出文件检查:")
    csv_path = Path(sim_csv)
    if csv_path.exists():
        size_kb = csv_path.stat().st_size / 1024
        print(f"    [OK] CSV 文件: {csv_path} ({size_kb:.1f} KB)")
    else:
        print(f"    [WARN] CSV 文件未生成: {csv_path}")

    img_dir = Path(sim_img)
    if img_dir.exists():
        img_count = len(list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png")))
        print(f"    [OK] 图片目录: {img_dir} ({img_count} 张图片)")
    else:
        print(f"    [WARN] 图片目录未生成: {img_dir}")

    # 最终判定
    print()
    pipeline_ok = (
        frame_count > 0
        and results.get('config')
        and results.get('detector')
        and results.get('transformer')
        and results.get('report_gen')
        and len(errors) == 0
    )

    if pipeline_ok and detection_count > 0:
        print("  >>> 结论: 实时管道端到端验证通过! <<<")
        print("      YOLO检测 -> 坐标转换 -> CSV/图片输出 全流程正常。")
        print("      接入真实 MQTT + RTSP 后即可上线。")
    elif pipeline_ok and detection_count == 0:
        print("  >>> 结论: 管道组件均正常初始化和运行，但未检测到目标。 <<<")
        print("      可能原因: 合成帧不含真实目标 / 视频中无目标 / 置信度阈值过高。")
        print("      建议: 使用包含检测目标的视频重新测试。")
    else:
        print("  >>> 结论: 管道验证未完全通过，请检查上述错误信息。 <<<")

    print("=" * 60)
    return results


def main():
    parser = argparse.ArgumentParser(
        description='实时管道模拟验证（无需 MQTT/RTSP）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--video', type=str, default=None,
                        help='本地视频文件路径（不指定则使用合成帧）')
    parser.add_argument('--config', type=str, default='./config',
                        help='配置文件目录 (默认: ./config)')
    parser.add_argument('--max-frames', type=int, default=100,
                        help='最大处理帧数 (默认: 100)')
    parser.add_argument('--frame-skip', type=int, default=15,
                        help='视频跳帧间隔 (默认: 15)')
    parser.add_argument('--lat', type=float, default=22.779954,
                        help='模拟起始纬度 (默认: 22.779954)')
    parser.add_argument('--lon', type=float, default=114.100891,
                        help='模拟起始经度 (默认: 114.100891)')
    parser.add_argument('--altitude', type=float, default=120.0,
                        help='模拟飞行高度/米 (默认: 120.0)')
    parser.add_argument('--speed', type=float, default=5.0,
                        help='模拟飞行速度 m/s (默认: 5.0)')
    parser.add_argument('--output-csv', type=str, default=None,
                        help='CSV 输出路径 (默认: ./data/output/csv/detections_simulation.csv)')
    parser.add_argument('--output-images', type=str, default=None,
                        help='图片输出目录 (默认: ./data/output/images_simulation/)')

    args = parser.parse_args()

    print_banner("实时管道模拟验证")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  视频: {args.video or '合成帧模式'}")
    print(f"  坐标: ({args.lat}, {args.lon}), 高度 {args.altitude}m")

    run_simulation(args)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  测试被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n  测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
