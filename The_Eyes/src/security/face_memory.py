#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Local face memory with OpenCV YuNet + SFace embeddings."""

from __future__ import annotations

import json
import logging
import threading
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np


class FaceMemoryStore:
    """Persist and cluster known people sightings on local disk."""

    # Model choice rationale: OpenCV YuNet + SFace runs fully local (no cloud API), works
    # on Windows CPU via OpenCV ONNX runtime path, and avoids dlib/face_recognition build friction.
    DETECTOR_URLS = [
        "https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx",
        "https://github.com/opencv/opencv_zoo/raw/refs/heads/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    ]
    RECOGNIZER_URLS = [
        "https://huggingface.co/opencv/face_recognition_sface/resolve/main/face_recognition_sface_2021dec.onnx",
        "https://github.com/opencv/opencv_zoo/raw/refs/heads/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
    ]

    def __init__(
        self,
        project_root: Path,
        data_dir: Path,
        enabled: bool = False,
        similarity_threshold: float = 0.42,
    ):
        self.project_root = Path(project_root)
        self.data_dir = Path(data_dir)
        self.enabled = bool(enabled)
        self.similarity_threshold = float(similarity_threshold)
        self.logger = logging.getLogger("the_eyes.face_memory")
        self._lock = threading.Lock()

        self.models_dir = self.data_dir / "models"
        self.persons_path = self.data_dir / "persons.json"
        self.sightings_path = self.data_dir / "sightings.json"
        self.detector_model_path = self.models_dir / "face_detection_yunet_2023mar.onnx"
        self.recognizer_model_path = self.models_dir / "face_recognition_sface_2021dec.onnx"

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self._detector = None
        self._recognizer = None
        self.runtime_ready = False
        self.runtime_error: Optional[str] = None

        if self.enabled:
            self._initialize_runtime()

    def _initialize_runtime(self) -> None:
        try:
            self._ensure_models()
            self._detector = cv2.FaceDetectorYN.create(
                str(self.detector_model_path), "", (320, 320), score_threshold=0.8, nms_threshold=0.3, top_k=5000
            )
            self._recognizer = cv2.FaceRecognizerSF.create(str(self.recognizer_model_path), "")
            self.runtime_ready = True
            self.runtime_error = None
        except Exception as exc:
            self.runtime_ready = False
            self.runtime_error = str(exc)
            self.logger.warning("Face memory runtime unavailable: %s", exc)

    def _ensure_models(self) -> None:
        self._ensure_model(self.detector_model_path, self.DETECTOR_URLS, min_size=100_000)
        self._ensure_model(self.recognizer_model_path, self.RECOGNIZER_URLS, min_size=10_000_000)

    def _ensure_model(self, path: Path, urls: List[str], min_size: int) -> None:
        if path.exists() and path.stat().st_size >= min_size:
            return
        last_error = None
        for url in urls:
            try:
                urllib.request.urlretrieve(url, path)
                if path.exists() and path.stat().st_size >= min_size:
                    return
                last_error = RuntimeError(f"downloaded too small: {path.stat().st_size} bytes")
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"Failed to download model {path.name}: {last_error}")

    def _load_rows(self, path: Path) -> List[Dict]:
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_rows(self, path: Path, rows: List[Dict]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)

    def _next_person_name(self, persons: List[Dict]) -> str:
        used = set()
        for row in persons:
            name = str(row.get("name", ""))
            if name.startswith("Person "):
                try:
                    used.add(int(name.split(" ")[1]))
                except Exception:
                    continue
        n = 1
        while n in used:
            n += 1
        return f"Person {n}"

    def _norm_embedding(self, emb: np.ndarray) -> List[float]:
        vec = np.asarray(emb, dtype=np.float32).reshape(-1)
        norm = float(np.linalg.norm(vec))
        if norm > 1e-8:
            vec = vec / norm
        return vec.astype(float).tolist()

    def _extract_faces(self, image_bgr: np.ndarray) -> List[Dict]:
        if not self.runtime_ready or self._detector is None or self._recognizer is None:
            return []
        h, w = image_bgr.shape[:2]
        self._detector.setInputSize((w, h))
        _, faces = self._detector.detect(image_bgr)
        if faces is None or len(faces) == 0:
            return []

        found: List[Dict] = []
        for face in faces:
            try:
                aligned = self._recognizer.alignCrop(image_bgr, face)
                embedding = self._recognizer.feature(aligned)
                bbox = [float(face[0]), float(face[1]), float(face[2]), float(face[3])]
                found.append(
                    {
                        "bbox": bbox,
                        "score": float(face[14]) if len(face) > 14 else 0.0,
                        "embedding": self._norm_embedding(embedding),
                    }
                )
            except Exception:
                continue
        return found

    def _person_best_similarity(self, person_id: str, embedding: List[float], sightings: List[Dict]) -> float:
        emb = np.asarray(embedding, dtype=np.float32)
        best = -1.0
        for row in sightings:
            if row.get("person_id") != person_id:
                continue
            other = row.get("embedding")
            if not isinstance(other, list) or not other:
                continue
            vec = np.asarray(other, dtype=np.float32)
            score = float(np.dot(emb, vec))
            if score > best:
                best = score
        return best

    def _create_person(self, persons: List[Dict], name: Optional[str] = None) -> Dict:
        person = {
            "id": f"person_{uuid.uuid4().hex[:8]}",
            "name": name or self._next_person_name(persons),
            "created_at": time.time(),
        }
        persons.append(person)
        return person

    def process_snapshot(
        self,
        camera_id: str,
        session_id: str,
        phase: str,
        snapshot_rel_path: str,
        timestamp: float,
    ) -> Dict:
        if not self.enabled:
            return {"enabled": False}
        if not self.runtime_ready:
            return {"enabled": True, "runtime_ready": False, "error": self.runtime_error}

        snapshot_path = (self.project_root / snapshot_rel_path).resolve()
        image = cv2.imread(str(snapshot_path))
        if image is None:
            return {"enabled": True, "runtime_ready": True, "faces": 0, "error": "snapshot_not_readable"}

        faces = self._extract_faces(image)
        if not faces:
            return {"enabled": True, "runtime_ready": True, "faces": 0}

        with self._lock:
            persons = self._load_rows(self.persons_path)
            sightings = self._load_rows(self.sightings_path)

            created = 0
            for face in faces:
                best_person = None
                best_score = -1.0
                for person in persons:
                    score = self._person_best_similarity(person["id"], face["embedding"], sightings)
                    if score > best_score:
                        best_score = score
                        best_person = person

                if best_person is None or best_score < self.similarity_threshold:
                    best_person = self._create_person(persons)
                    created += 1
                    best_score = 1.0

                sightings.append(
                    {
                        "id": f"sighting_{uuid.uuid4().hex[:10]}",
                        "person_id": best_person["id"],
                        "camera_id": camera_id,
                        "session_id": session_id,
                        "phase": phase,
                        "snapshot_path": snapshot_rel_path,
                        "timestamp": float(timestamp),
                        "bbox": face["bbox"],
                        "score": best_score,
                        "embedding": face["embedding"],
                        "source": "motion_snapshot",
                    }
                )

            self._save_rows(self.persons_path, persons)
            self._save_rows(self.sightings_path, sightings[-5000:])
            return {
                "enabled": True,
                "runtime_ready": True,
                "faces": len(faces),
                "new_people": created,
            }

    def enroll_from_snapshot(
        self, snapshot_rel_path: str, camera_id: str, person_id: Optional[str] = None
    ) -> Dict:
        if not self.enabled:
            return {"enabled": False}
        if not self.runtime_ready:
            return {"enabled": True, "runtime_ready": False, "error": self.runtime_error}

        snapshot_path = (self.project_root / snapshot_rel_path).resolve()
        image = cv2.imread(str(snapshot_path))
        if image is None:
            raise FileNotFoundError(snapshot_rel_path)

        faces = self._extract_faces(image)
        if not faces:
            return {"status": "success", "no_face": True}

        faces.sort(key=lambda f: f["bbox"][2] * f["bbox"][3], reverse=True)
        face = faces[0]

        with self._lock:
            persons = self._load_rows(self.persons_path)
            sightings = self._load_rows(self.sightings_path)
            person = next((p for p in persons if p.get("id") == person_id), None)
            if person is None:
                person = self._create_person(persons)

            sighting = {
                "id": f"sighting_{uuid.uuid4().hex[:10]}",
                "person_id": person["id"],
                "camera_id": camera_id,
                "session_id": None,
                "phase": "manual_enroll",
                "snapshot_path": snapshot_rel_path,
                "timestamp": time.time(),
                "bbox": face["bbox"],
                "score": 1.0,
                "embedding": face["embedding"],
                "source": "manual_enroll",
            }
            sightings.append(sighting)

            self._save_rows(self.persons_path, persons)
            self._save_rows(self.sightings_path, sightings[-5000:])
            return {"status": "success", "person": person, "sighting": sighting}

    def get_people_summary(self) -> List[Dict]:
        with self._lock:
            persons = self._load_rows(self.persons_path)
            sightings = self._load_rows(self.sightings_path)
        grouped: Dict[str, List[Dict]] = {}
        for row in sightings:
            grouped.setdefault(row.get("person_id"), []).append(row)
        out = []
        for person in persons:
            person_sightings = sorted(grouped.get(person["id"], []), key=lambda r: r.get("timestamp", 0), reverse=True)
            out.append(
                {
                    **person,
                    "sightings": len(person_sightings),
                    "last_seen_at": person_sightings[0]["timestamp"] if person_sightings else None,
                    "sample_snapshot": person_sightings[0]["snapshot_path"] if person_sightings else None,
                }
            )
        out.sort(key=lambda r: (r.get("last_seen_at") or 0), reverse=True)
        return out

    def list_sightings(self, person_id: Optional[str] = None, limit: int = 200) -> List[Dict]:
        with self._lock:
            sightings = self._load_rows(self.sightings_path)
        rows = sightings
        if person_id:
            rows = [row for row in rows if row.get("person_id") == person_id]
        rows = sorted(rows, key=lambda r: r.get("timestamp", 0), reverse=True)
        return rows[:limit]

    def rename_person(self, person_id: str, name: str) -> Dict:
        with self._lock:
            persons = self._load_rows(self.persons_path)
            person = next((p for p in persons if p.get("id") == person_id), None)
            if person is None:
                raise KeyError(person_id)
            person["name"] = str(name).strip() or person["name"]
            self._save_rows(self.persons_path, persons)
            return person

    def merge_people(self, source_person_id: str, target_person_id: str) -> Dict:
        if source_person_id == target_person_id:
            return {"status": "success", "moved": 0}
        with self._lock:
            persons = self._load_rows(self.persons_path)
            sightings = self._load_rows(self.sightings_path)
            target = next((p for p in persons if p.get("id") == target_person_id), None)
            source = next((p for p in persons if p.get("id") == source_person_id), None)
            if target is None:
                raise KeyError(target_person_id)
            if source and self._is_auto_person_name(target.get("name", "")) and not self._is_auto_person_name(
                source.get("name", "")
            ):
                target["name"] = str(source.get("name", "")).strip() or target["name"]
            moved = 0
            for row in sightings:
                if row.get("person_id") == source_person_id:
                    row["person_id"] = target_person_id
                    moved += 1
            persons = [p for p in persons if p.get("id") != source_person_id]
            self._save_rows(self.persons_path, persons)
            self._save_rows(self.sightings_path, sightings[-5000:])
            return {"status": "success", "moved": moved}

    def reassign_sighting(
        self, sighting_id: str, target_person_id: Optional[str] = None, create_person_name: Optional[str] = None
    ) -> Dict:
        with self._lock:
            persons = self._load_rows(self.persons_path)
            sightings = self._load_rows(self.sightings_path)
            sighting = next((s for s in sightings if s.get("id") == sighting_id), None)
            if sighting is None:
                raise KeyError(sighting_id)

            target = None
            if target_person_id:
                target = next((p for p in persons if p.get("id") == target_person_id), None)
            if target is None:
                target = self._create_person(persons, create_person_name)

            sighting["person_id"] = target["id"]
            self._save_rows(self.persons_path, persons)
            self._save_rows(self.sightings_path, sightings[-5000:])
            return {"status": "success", "sighting": sighting, "person": target}

    def _is_auto_person_name(self, name: str) -> bool:
        return str(name).startswith("Person ")

    def _pick_merge_target(self, id_a: str, id_b: str, summaries: Dict[str, Dict]) -> Tuple[str, str]:
        """Return (target_id, source_id) — target profile is kept."""
        a = summaries[id_a]
        b = summaries[id_b]
        a_auto = self._is_auto_person_name(a.get("name", ""))
        b_auto = self._is_auto_person_name(b.get("name", ""))
        if not a_auto and b_auto:
            return id_a, id_b
        if a_auto and not b_auto:
            return id_b, id_a
        if a.get("sightings", 0) >= b.get("sightings", 0):
            return id_a, id_b
        return id_b, id_a

    def _person_centroid_embedding(self, person_id: str, sightings: List[Dict]) -> Optional[np.ndarray]:
        vecs = []
        for row in sightings:
            if row.get("person_id") != person_id:
                continue
            emb = row.get("embedding")
            if isinstance(emb, list) and emb:
                vecs.append(np.asarray(emb, dtype=np.float32))
        if not vecs:
            return None
        centroid = np.mean(np.stack(vecs, axis=0), axis=0)
        norm = float(np.linalg.norm(centroid))
        if norm > 1e-8:
            centroid = centroid / norm
        return centroid

    def find_similar_pairs(self, min_similarity: Optional[float] = None) -> List[Dict]:
        """Return person pairs that look like the same face."""
        threshold = self.similarity_threshold if min_similarity is None else float(min_similarity)
        with self._lock:
            persons = self._load_rows(self.persons_path)
            sightings = self._load_rows(self.sightings_path)

        grouped: Dict[str, List[Dict]] = {}
        for row in sightings:
            grouped.setdefault(row.get("person_id"), []).append(row)

        centroids: Dict[str, np.ndarray] = {}
        summaries: Dict[str, Dict] = {}
        for person in persons:
            pid = person["id"]
            centroid = self._person_centroid_embedding(pid, sightings)
            if centroid is None:
                continue
            centroids[pid] = centroid
            person_sightings = sorted(grouped.get(pid, []), key=lambda r: r.get("timestamp", 0), reverse=True)
            summaries[pid] = {
                **person,
                "sightings": len(person_sightings),
                "sample_snapshot": person_sightings[0]["snapshot_path"] if person_sightings else None,
                "sample_bbox": person_sightings[0].get("bbox") if person_sightings else None,
            }

        pairs: List[Dict] = []
        person_ids = list(centroids.keys())
        for i, id_a in enumerate(person_ids):
            for id_b in person_ids[i + 1 :]:
                similarity = float(np.dot(centroids[id_a], centroids[id_b]))
                if similarity < threshold:
                    continue
                a = summaries[id_a]
                b = summaries[id_b]
                target_id, source_id = self._pick_merge_target(id_a, id_b, summaries)
                pairs.append(
                    {
                        "similarity": round(similarity, 4),
                        "similarity_pct": round(similarity * 100, 1),
                        "source_person_id": source_id,
                        "target_person_id": target_id,
                        "source": summaries[source_id],
                        "target": summaries[target_id],
                    }
                )
        pairs.sort(key=lambda row: row["similarity"], reverse=True)
        return pairs

    def merge_all_similar_pairs(self, min_similarity: Optional[float] = None) -> Dict:
        """Merge every similar pair (source -> target with more sightings)."""
        pairs = self.find_similar_pairs(min_similarity=min_similarity)
        merged = 0
        moved = 0
        for pair in pairs:
            result = self.merge_people(pair["source_person_id"], pair["target_person_id"])
            if result.get("moved", 0) > 0 or pair["source_person_id"] != pair["target_person_id"]:
                merged += 1
                moved += int(result.get("moved", 0))
        return {"status": "success", "pairs_merged": merged, "sightings_moved": moved}

    def attach_session_detections(self, sessions: List[Dict]) -> List[Dict]:
        """Attach face_detection metadata to motion session rows."""
        with self._lock:
            persons_by_id = {p["id"]: p for p in self._load_rows(self.persons_path)}
            sightings = self._load_rows(self.sightings_path)

        grouped: Dict[str, List[Dict]] = {}
        by_snapshot: Dict[str, List[Dict]] = {}
        for row in sightings:
            session_id = row.get("session_id")
            camera_id = row.get("camera_id") or ""
            if session_id:
                key = f"{camera_id}::{session_id}"
                grouped.setdefault(key, []).append(row)
            snapshot_path = row.get("snapshot_path")
            if snapshot_path:
                by_snapshot.setdefault(snapshot_path, []).append(row)

        enriched: List[Dict] = []
        for session in sessions:
            key = f"{session.get('camera_id')}::{session.get('session_id')}"
            rows = list(grouped.get(key, []))
            seen_ids = {row.get("id") for row in rows}
            for path in (session.get("first_snapshot"), session.get("last_snapshot")):
                if not path:
                    continue
                for row in by_snapshot.get(path, []):
                    if row.get("id") not in seen_ids:
                        rows.append(row)
                        seen_ids.add(row.get("id"))
            people_map: Dict[str, Dict] = {}
            for row in rows:
                person_id = row.get("person_id")
                if not person_id or person_id in people_map:
                    continue
                person = persons_by_id.get(person_id)
                people_map[person_id] = {
                    "id": person_id,
                    "name": (person or {}).get("name", person_id),
                }

            people = list(people_map.values())
            session_copy = dict(session)
            session_copy["face_detection"] = {
                "detected": len(people) > 0,
                "people": people,
                "sightings": len(rows),
            }
            enriched.append(session_copy)
        return enriched
