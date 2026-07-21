"""
Persistence for charge/discharge cycle history in the unified system.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict


class ChargeCycleRepository:
    """Read/write access for charge cycle data."""

    def __init__(self, file_path: str | None = None):
        default_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "charge_cycles.json"
        )
        self.file_path = file_path or default_path

    def load(self) -> Dict[str, Any]:
        """Load cycle data, creating defaults when missing/invalid."""
        default_data: Dict[str, Any] = {
            "charge_cycles": [],
            "discharge_cycles": [],
            "metadata": {
                "updated_at": None,
                "version": 2,
                "full_battery_percent": 100,
                "full_battery_percent_learned": None,
                "auto_apply_learned_full": True,
            },
        }

        if not os.path.exists(self.file_path):
            self.save(default_data)
            return default_data

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return default_data
            data.setdefault("charge_cycles", [])
            data.setdefault("discharge_cycles", [])
            metadata = dict(data.setdefault("metadata", {}))
            metadata.setdefault("updated_at", None)
            metadata.setdefault("version", 2)
            metadata.setdefault("full_battery_percent", 100)
            metadata.setdefault("full_battery_percent_learned", None)
            metadata.setdefault("auto_apply_learned_full", True)
            data["metadata"] = metadata
            return data
        except Exception:
            return default_data

    def save(self, data: Dict[str, Any]) -> None:
        """Persist cycle data."""
        data = dict(data)
        metadata = dict(data.get("metadata", {}))
        metadata["updated_at"] = datetime.now().isoformat()
        metadata.setdefault("version", 1)
        data["metadata"] = metadata

        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

