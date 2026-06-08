import subprocess
import tempfile
from pathlib import Path
from typing import Protocol

import open3d as o3d


class ReconstructionBackend(Protocol):
    name: str

    def run(self, engine) -> bool:
        ...


class ColmapSfMBackend:
    name = "colmap_sfm"

    def run(self, engine) -> bool:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            for i, frame in enumerate(engine.keyframes):
                import cv2
                cv2.imwrite(str(temp_dir_path / f"frame_{i:06d}.jpg"), frame)

            try:
                subprocess.run(
                    ["where", "colmap"],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            except subprocess.CalledProcessError as exc:
                raise FileNotFoundError("COLMAP executable not found in PATH") from exc

            colmap_cmd = [
                "colmap", "automatic_reconstructor",
                "--workspace_path", str(temp_dir_path),
                "--image_path", str(temp_dir_path),
            ]
            subprocess.run(colmap_cmd, check=True)

            sparse_model_path = temp_dir_path / "sparse" / "0"
            if sparse_model_path.exists():
                pcd = o3d.io.read_point_cloud(str(sparse_model_path / "points3D.ply"))
                engine.point_cloud += pcd
                engine.update_visualization()

            dense_model_path = temp_dir_path / "dense" / "0"
            if dense_model_path.exists():
                dense_pcd = o3d.io.read_point_cloud(str(dense_model_path / "fused.ply"))
                engine.point_cloud += dense_pcd
                engine.mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(
                    engine.point_cloud, alpha=0.05
                )
                engine.update_visualization()
                return True

            return len(engine.point_cloud.points) > 0


class ManualSfMBackend:
    name = "manual_sfm"

    def run(self, engine) -> bool:
        engine._manual_reconstruction()
        return len(engine.point_cloud.points) > 0


class NeuralStreamingBackend:
    """Scaffold for a future feed-forward streaming backend."""

    name = "neural_streaming_scaffold"

    def __init__(self, window_size: int = 128, keyframe_interval: int = 2):
        self.window_size = window_size
        self.keyframe_interval = keyframe_interval
        self._memory_cache = []

    def ingest_frame(self, frame_idx: int, frame):
        if frame_idx % self.keyframe_interval == 0:
            self._memory_cache.append((frame_idx, frame))
        if len(self._memory_cache) > self.window_size:
            self._memory_cache = self._memory_cache[-self.window_size:]

    def run(self, engine) -> bool:
        # Placeholder: this backend defines interfaces and runtime knobs only.
        for idx, frame in enumerate(engine.keyframes):
            self.ingest_frame(idx, frame)
        raise NotImplementedError(
            "NeuralStreamingBackend is a scaffold. Integrate a model checkpoint and inference pipeline."
        )
