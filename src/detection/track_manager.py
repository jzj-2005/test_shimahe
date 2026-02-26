"""
目标跟踪管理器（延迟保存策略）

在YOLO推理阶段为每个检测目标维护跟踪状态缓冲区，
目标离开画面后才输出其生命周期内最优的检测结果，
从源头消除重复检测，减少CSV写入、图像截图和坐标转换。
"""

import time
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger


@dataclass
class TrackState:
    """单个跟踪目标的状态缓冲"""
    track_id: int
    best_detection: Dict[str, Any]
    best_frame: Optional[np.ndarray]
    best_pose: Dict[str, Any]
    best_frame_number: int
    best_score: float
    first_seen: int
    last_seen: int
    total_appearances: int = 1


class TrackManager:
    """
    目标跟踪管理器

    核心策略：延迟保存（Deferred Save）
    - 每帧更新跟踪缓冲区，持续追踪最优质量的检测
    - 目标离开画面（跟踪丢失）后，才将最优检测输出
    - 保证保存的一定是目标最完整、最高质量的那一帧
    """

    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        self.active_tracks: Dict[int, TrackState] = {}
        self.lost_threshold = config.get('lost_threshold', 30)
        self.edge_penalty = config.get('edge_penalty', 0.3)
        self.min_track_frames = config.get('min_track_frames', 3)
        self.crop_buffer = config.get('crop_buffer', True)

        self._saved_count = 0
        self._discarded_count = 0
        self._total_updates = 0

        logger.info(
            f"TrackManager initialized: lost_threshold={self.lost_threshold}, "
            f"edge_penalty={self.edge_penalty}, min_track_frames={self.min_track_frames}"
        )

    def update(
        self,
        detections: List[Dict[str, Any]],
        frame: np.ndarray,
        pose: Dict[str, Any],
        frame_number: int
    ):
        """
        每帧调用：用当前帧的检测结果更新所有活跃跟踪的缓冲区。

        Args:
            detections: 带有 track_id 的检测结果列表
            frame: 当前帧图像
            pose: 当前帧位姿数据
            frame_number: 当前帧号
        """
        self._total_updates += 1
        seen_ids = set()

        for det in detections:
            tid = det.get('track_id')
            if tid is None:
                continue

            seen_ids.add(tid)
            score = self._calc_quality(det)

            if tid not in self.active_tracks:
                buffered_frame = self._prepare_frame_buffer(frame, det)
                self.active_tracks[tid] = TrackState(
                    track_id=tid,
                    best_detection=det.copy(),
                    best_frame=buffered_frame,
                    best_pose=pose.copy() if pose else {},
                    best_frame_number=frame_number,
                    best_score=score,
                    first_seen=frame_number,
                    last_seen=frame_number,
                    total_appearances=1
                )
            else:
                state = self.active_tracks[tid]
                state.last_seen = frame_number
                state.total_appearances += 1

                if score > state.best_score:
                    state.best_detection = det.copy()
                    state.best_frame = self._prepare_frame_buffer(frame, det)
                    state.best_pose = pose.copy() if pose else {}
                    state.best_frame_number = frame_number
                    state.best_score = score

    def flush_lost_tracks(
        self,
        current_frame: int,
        transformer,
        report_gen
    ) -> int:
        """
        每帧调用：检查已消失的目标，将其最优检测输出到CSV和截图。

        Args:
            current_frame: 当前帧号
            transformer: 坐标转换器实例
            report_gen: 报告生成器实例

        Returns:
            本次刷写的目标数量
        """
        to_flush = []
        for tid, state in self.active_tracks.items():
            if current_frame - state.last_seen > self.lost_threshold:
                to_flush.append(tid)

        flushed = 0
        for tid in to_flush:
            state = self.active_tracks.pop(tid)
            if self._should_output(state):
                self._output_track(state, transformer, report_gen)
                flushed += 1
            else:
                self._discarded_count += 1
                logger.debug(
                    f"Track {tid} discarded: only appeared {state.total_appearances} frames "
                    f"(min={self.min_track_frames})"
                )

        return flushed

    def flush_all(self, transformer, report_gen) -> int:
        """
        管线结束时调用：输出所有剩余缓冲目标。

        Args:
            transformer: 坐标转换器实例
            report_gen: 报告生成器实例

        Returns:
            刷写的目标总数
        """
        flushed = 0
        for tid, state in list(self.active_tracks.items()):
            if self._should_output(state):
                self._output_track(state, transformer, report_gen)
                flushed += 1
            else:
                self._discarded_count += 1

        self.active_tracks.clear()
        logger.info(f"TrackManager flush_all: saved {flushed} tracks")
        return flushed

    def _should_output(self, state: TrackState) -> bool:
        """判断跟踪目标是否满足输出条件"""
        return state.total_appearances >= self.min_track_frames

    def _output_track(self, state: TrackState, transformer, report_gen):
        """将一个跟踪目标的最优检测输出"""
        try:
            det = state.best_detection
            det['track_id'] = state.track_id
            det_list = [det]

            det_list = transformer.transform_detections(det_list, state.best_pose)
            report_gen.save(det_list, state.best_frame, state.best_pose, state.best_frame_number)
            self._saved_count += 1

            logger.debug(
                f"Track {state.track_id} saved: score={state.best_score:.3f}, "
                f"appeared frames {state.first_seen}-{state.last_seen} "
                f"({state.total_appearances} times), best at frame {state.best_frame_number}"
            )
        except Exception as e:
            logger.error(f"Failed to output track {state.track_id}: {e}")

    def _calc_quality(self, detection: Dict[str, Any]) -> float:
        """
        计算检测质量评分。

        完整可见的高置信度目标远优于边缘半截目标。
        score = confidence * edge_factor * (1 + area_bonus)
        """
        conf = detection.get('confidence', 0.0)
        is_on_edge = detection.get('is_on_edge', False)
        edge_factor = self.edge_penalty if is_on_edge else 1.0

        corners = detection.get('corners', [])
        area_bonus = 0.0
        if len(corners) >= 4:
            x_coords = [c[0] for c in corners]
            y_coords = [c[1] for c in corners]
            w = max(x_coords) - min(x_coords)
            h = max(y_coords) - min(y_coords)
            area_bonus = min((w * h) / 1e6, 0.5)

        return conf * edge_factor * (1.0 + area_bonus)

    def _prepare_frame_buffer(
        self,
        frame: np.ndarray,
        detection: Dict[str, Any]
    ) -> np.ndarray:
        """
        准备帧缓冲：裁剪目标区域以节省内存，或保留完整帧。

        裁剪模式下每个目标约占 50-200KB（vs 完整帧 6MB），
        同时追踪 50 个目标约 2.5-10MB（vs 300MB）。
        """
        if not self.crop_buffer:
            return frame.copy()

        corners = detection.get('corners', [])
        if len(corners) < 4:
            xyxy = detection.get('xyxy', [])
            if len(xyxy) == 4:
                x1, y1, x2, y2 = [int(v) for v in xyxy]
            else:
                return frame.copy()
        else:
            x_coords = [c[0] for c in corners]
            y_coords = [c[1] for c in corners]
            x1, y1 = int(min(x_coords)), int(min(y_coords))
            x2, y2 = int(max(x_coords)), int(max(y_coords))

        h, w = frame.shape[:2]
        pad = 50
        x1 = max(0, x1 - pad)
        y1 = max(0, y1 - pad)
        x2 = min(w, x2 + pad)
        y2 = min(h, y2 + pad)

        return frame[y1:y2, x1:x2].copy()

    def get_active_count(self) -> int:
        """获取当前活跃跟踪数量"""
        return len(self.active_tracks)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'active_tracks': len(self.active_tracks),
            'total_saved': self._saved_count,
            'total_discarded': self._discarded_count,
            'total_frame_updates': self._total_updates,
        }

    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        logger.info("=== TrackManager Statistics ===")
        logger.info(f"Active tracks: {stats['active_tracks']}")
        logger.info(f"Total saved: {stats['total_saved']}")
        logger.info(f"Total discarded (short-lived): {stats['total_discarded']}")
        logger.info(f"Total frame updates: {stats['total_frame_updates']}")
        if self._saved_count + self._discarded_count > 0:
            total = self._saved_count + self._discarded_count
            logger.info(f"Save rate: {self._saved_count / total * 100:.1f}%")
