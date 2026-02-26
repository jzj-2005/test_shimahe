"""
目标跟踪去重功能验证脚本

验证 TrackManager 延迟保存策略的核心逻辑：
1. 模块导入检查
2. TrackManager 单元测试（模拟多帧跟踪场景）
3. YOLODetector tracking 接口检查
4. 配置文件完整性检查
5. 管线集成检查
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [OK] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}" + (f" - {detail}" if detail else ""))


# ============================================================
print("=" * 60)
print("1. Module Import Check")
print("=" * 60)

TrackManager = None
TrackState = None
YOLODetector = None

try:
    from src.detection.track_manager import TrackManager, TrackState
    check("TrackManager import", True)
except ImportError as e:
    if 'ultralytics' in str(e):
        # __init__.py triggers yolo_detector import; import directly
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "track_manager",
            os.path.join("src", "detection", "track_manager.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        TrackManager = mod.TrackManager
        TrackState = mod.TrackState
        check("TrackManager import (direct, ultralytics N/A)", True)
    else:
        check("TrackManager import", False, str(e))
except Exception as e:
    check("TrackManager import", False, str(e))

has_ultralytics = False
try:
    from src.detection.yolo_detector import YOLODetector
    check("YOLODetector import", True)
    has_ultralytics = True
except ImportError as e:
    if 'ultralytics' in str(e):
        check("YOLODetector import (ultralytics not installed, skip)", True)
    else:
        check("YOLODetector import", False, str(e))
except Exception as e:
    check("YOLODetector import", False, str(e))

try:
    from src.detection import TrackManager as TM2
    check("TrackManager via __init__", TM2 is not None)
except ImportError as e:
    if 'ultralytics' in str(e):
        check("TrackManager via __init__ (ultralytics not installed, skip)", True)
    else:
        check("TrackManager via __init__", False, str(e))
except Exception as e:
    check("TrackManager via __init__", False, str(e))

# ============================================================
print("\n" + "=" * 60)
print("2. TrackManager Unit Test - Deferred Save Simulation")
print("=" * 60)


class MockTransformer:
    """Mock coordinate transformer"""
    def transform_detections(self, detections, pose):
        for d in detections:
            d['geo_coords'] = [(23.0, 113.0)] * 4
            d['center_geo'] = (23.0, 113.0)
        return detections


class MockReportGen:
    """Mock report generator that records saves"""
    def __init__(self):
        self.saved = []

    def save(self, detections, frame, pose, frame_number):
        for d in detections:
            self.saved.append({
                'track_id': d.get('track_id'),
                'confidence': d.get('confidence'),
                'frame_number': frame_number,
                'is_on_edge': d.get('is_on_edge', False),
            })


if TrackManager is None:
    print("  [SKIP] TrackManager not imported, cannot run unit tests")
    print("\n" + "=" * 60)
    print(f"RESULT: {passed} passed, {failed} failed (some tests skipped)")
    print("=" * 60)
    sys.exit(1)

config = {
    'lost_threshold': 5,
    'edge_penalty': 0.3,
    'min_track_frames': 2,
    'crop_buffer': False,
}

tm = TrackManager(config)
transformer = MockTransformer()
report_gen = MockReportGen()

dummy_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
dummy_pose = {'latitude': 23.0, 'longitude': 113.0, 'altitude': 100.0, 'timestamp': 0}

# Simulate: object appears at edge (half visible) then becomes fully visible
# Frame 0: edge detection, low confidence
tm.update([{
    'track_id': 1,
    'class_id': 8,
    'class_name': 'Sheds',
    'confidence': 0.55,
    'corners': [(1800, 200), (1920, 200), (1920, 600), (1800, 600)],
    'is_on_edge': True,
    'edge_positions': ['right'],
}], dummy_frame, dummy_pose, 0)

check("Track created at frame 0", tm.get_active_count() == 1)
check("No saves yet at frame 0", len(report_gen.saved) == 0)

# Frame 5: better detection, still on edge
tm.update([{
    'track_id': 1,
    'class_id': 8,
    'class_name': 'Sheds',
    'confidence': 0.72,
    'corners': [(1600, 200), (1920, 200), (1920, 600), (1600, 600)],
    'is_on_edge': True,
    'edge_positions': ['right'],
}], dummy_frame, dummy_pose, 5)

check("Still 1 active track", tm.get_active_count() == 1)
check("Buffer updated (edge penalty)", tm.active_tracks[1].best_score > 0.15)

# Frame 10: fully visible, high confidence, not on edge
tm.update([{
    'track_id': 1,
    'class_id': 8,
    'class_name': 'Sheds',
    'confidence': 0.88,
    'corners': [(500, 200), (1200, 200), (1200, 600), (500, 600)],
    'is_on_edge': False,
    'edge_positions': [],
}], dummy_frame, dummy_pose, 10)

best_score = tm.active_tracks[1].best_score
check("Best score updated (full visibility)", best_score > 0.8)
check("Best frame is 10", tm.active_tracks[1].best_frame_number == 10)

# Frame 15: leaving frame, worse quality
tm.update([{
    'track_id': 1,
    'class_id': 8,
    'class_name': 'Sheds',
    'confidence': 0.70,
    'corners': [(0, 200), (300, 200), (300, 600), (0, 600)],
    'is_on_edge': True,
    'edge_positions': ['left'],
}], dummy_frame, dummy_pose, 15)

check("Best frame still 10 (no downgrade)", tm.active_tracks[1].best_frame_number == 10)

# Frame 16-20: object gone, but lost_threshold=5
for f in range(16, 21):
    tm.update([], dummy_frame, dummy_pose, f)
    tm.flush_lost_tracks(f, transformer, report_gen)

check("Still active (within threshold)", tm.get_active_count() == 1)

# Frame 21: now lost_threshold exceeded (last_seen=15, current=21, diff=6 > 5)
tm.flush_lost_tracks(21, transformer, report_gen)
check("Track flushed after lost_threshold", tm.get_active_count() == 0)
check("Exactly 1 save output", len(report_gen.saved) == 1)
check("Saved confidence is 0.88 (best)", 
      abs(report_gen.saved[0]['confidence'] - 0.88) < 0.01)
check("Saved frame_number is 10", report_gen.saved[0]['frame_number'] == 10)

# ============================================================
print("\n" + "=" * 60)
print("3. Short-lived Track Filtering (min_track_frames)")
print("=" * 60)

tm2 = TrackManager({'lost_threshold': 3, 'min_track_frames': 3, 'crop_buffer': False})
rg2 = MockReportGen()

# Single-frame detection (noise/false positive)
tm2.update([{
    'track_id': 99,
    'class_id': 0,
    'class_name': 'Test',
    'confidence': 0.9,
    'corners': [(100, 100), (200, 100), (200, 200), (100, 200)],
    'is_on_edge': False,
}], dummy_frame, dummy_pose, 0)

for f in range(1, 10):
    tm2.flush_lost_tracks(f, transformer, rg2)

check("Short-lived track discarded (1 frame < min 3)", len(rg2.saved) == 0)

# ============================================================
print("\n" + "=" * 60)
print("4. flush_all on Pipeline End")
print("=" * 60)

tm3 = TrackManager({'lost_threshold': 999, 'min_track_frames': 1, 'crop_buffer': False})
rg3 = MockReportGen()

tm3.update([{
    'track_id': 10,
    'class_id': 4,
    'class_name': 'Industrial',
    'confidence': 0.75,
    'corners': [(100, 100), (500, 100), (500, 400), (100, 400)],
    'is_on_edge': False,
}], dummy_frame, dummy_pose, 0)

check("Active before flush_all", tm3.get_active_count() == 1)
tm3.flush_all(transformer, rg3)
check("No active after flush_all", tm3.get_active_count() == 0)
check("1 save from flush_all", len(rg3.saved) == 1)

# ============================================================
print("\n" + "=" * 60)
print("5. Config File Check")
print("=" * 60)

try:
    import yaml
    with open('config/yolo_config.yaml', 'r', encoding='utf-8') as f:
        yolo_cfg = yaml.safe_load(f)
    tracking_cfg = yolo_cfg.get('tracking', {})
    check("tracking.enabled exists", 'enabled' in tracking_cfg)
    check("tracking.tracker exists", 'tracker' in tracking_cfg)
    check("tracking.lost_threshold exists", 'lost_threshold' in tracking_cfg)
    check("tracking.edge_penalty exists", 'edge_penalty' in tracking_cfg)
    check("tracking.min_track_frames exists", 'min_track_frames' in tracking_cfg)
    check("tracking.crop_buffer exists", 'crop_buffer' in tracking_cfg)
except Exception as e:
    check("Config file check", False, str(e))

# ============================================================
print("\n" + "=" * 60)
print("6. CSV Writer track_id Field Check")
print("=" * 60)

try:
    from src.output.csv_writer import CSVWriter
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w')
    tmp.close()
    writer = CSVWriter(tmp.name, "overwrite")
    check("track_id in CSV fieldnames", 'track_id' in writer.fieldnames)
    writer.close()
    os.unlink(tmp.name)
except Exception as e:
    check("CSV Writer check", False, str(e))

# ============================================================
print("\n" + "=" * 60)
print("7. YOLODetector Interface Check")
print("=" * 60)

if YOLODetector is not None:
    check("detect_with_tracking method exists", hasattr(YOLODetector, 'detect_with_tracking'))
    check("reset_tracker method exists", hasattr(YOLODetector, 'reset_tracker'))
    check("tracker_type parameter", 'tracker_type' in YOLODetector.__init__.__code__.co_varnames)
else:
    # Check source code directly when ultralytics not available
    try:
        with open('src/detection/yolo_detector.py', 'r', encoding='utf-8') as f:
            src_code = f.read()
        check("detect_with_tracking in source", 'def detect_with_tracking' in src_code)
        check("reset_tracker in source", 'def reset_tracker' in src_code)
        check("tracker_type in __init__ source", 'tracker_type' in src_code)
    except Exception as e:
        check("YOLODetector source check", False, str(e))

# ============================================================
print("\n" + "=" * 60)
print("8. Pipeline Integration Check (source-level)")
print("=" * 60)

try:
    with open('src/offline_pipeline.py', 'r', encoding='utf-8') as f:
        src = f.read()
    check("OfflinePipeline imports TrackManager", 'TrackManager' in src)
    check("OfflinePipeline has tracking_enabled", 'tracking_enabled' in src)
    check("OfflinePipeline calls flush_all", 'flush_all' in src)
    check("OfflinePipeline calls detect_with_tracking", 'detect_with_tracking' in src)
except Exception as e:
    check("OfflinePipeline check", False, str(e))

try:
    with open('src/realtime_pipeline.py', 'r', encoding='utf-8') as f:
        src_rt = f.read()
    check("RealtimePipeline imports TrackManager", 'TrackManager' in src_rt)
    check("RealtimePipeline has tracking_enabled", 'tracking_enabled' in src_rt)
    check("RealtimePipeline calls flush_all", 'flush_all' in src_rt)
    check("RealtimePipeline calls detect_with_tracking", 'detect_with_tracking' in src_rt)
except Exception as e:
    check("RealtimePipeline check", False, str(e))

# ============================================================
print("\n" + "=" * 60)
print(f"RESULT: {passed} passed, {failed} failed")
print("=" * 60)

if failed == 0:
    print("[SUCCESS] All tracking dedup tests passed!")
else:
    print(f"[WARNING] {failed} test(s) failed, please review.")

sys.exit(0 if failed == 0 else 1)
