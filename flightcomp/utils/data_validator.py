"""
Data Validator for Flightcomp
Runs structural/referential checks and optional AI (Ollama) content validation
on airports, scenarios, checklists, and training records.
"""

import os
import json
import requests
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class Severity(Enum):
    PASS = "pass"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationResult:
    """Single validation result."""
    entity_id: str
    category: str  # airports, scenarios, checklists, training_records
    severity: Severity
    message: str
    detail: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "category": self.category,
            "severity": self.severity.value,
            "message": self.message,
            "detail": self.detail,
        }


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_path(*parts: str) -> str:
    return os.path.join(_project_root(), "data", *parts)


def validate_airports_structural(
    results: List[ValidationResult],
    airports_data: Optional[Dict[str, Any]] = None,
) -> None:
    """Structural checks for airport_info.json."""
    path = _data_path("airports", "airport_info.json")
    if not os.path.exists(path):
        results.append(ValidationResult(
            entity_id="airport_info.json",
            category="airports",
            severity=Severity.ERROR,
            message="File not found",
            detail=path,
        ))
        return
    try:
        if airports_data is not None:
            data = airports_data
        else:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        if "airports" not in data:
            results.append(ValidationResult(
                entity_id="airport_info.json",
                category="airports",
                severity=Severity.ERROR,
                message="Missing 'airports' key",
            ))
            return
        for ap in data["airports"]:
            icao = ap.get("airport_icao") or ap.get("icao")
            if not icao:
                results.append(ValidationResult(
                    entity_id=ap.get("airport_name", "?"),
                    category="airports",
                    severity=Severity.ERROR,
                    message="Airport missing airport_icao",
                ))
            else:
                results.append(ValidationResult(
                    entity_id=icao,
                    category="airports",
                    severity=Severity.PASS,
                    message="OK",
                ))
    except json.JSONDecodeError as e:
        results.append(ValidationResult(
            entity_id="airport_info.json",
            category="airports",
            severity=Severity.ERROR,
            message="Invalid JSON",
            detail=str(e),
        ))
    except Exception as e:
        results.append(ValidationResult(
            entity_id="airport_info.json",
            category="airports",
            severity=Severity.ERROR,
            message="Read error",
            detail=str(e),
        ))


def validate_scenarios_structural(
    results: List[ValidationResult],
    airport_icaos: Optional[set] = None,
    checklist_ids: Optional[set] = None,
) -> None:
    """Structural and referential checks for scenario JSON files."""
    if airport_icaos is None:
        path = _data_path("airports", "airport_info.json")
        airport_icaos = set()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for ap in data.get("airports", []):
                        icao = ap.get("airport_icao")
                        if icao:
                            airport_icaos.add(icao.upper())
            except Exception:
                pass
    if checklist_ids is None:
        checklist_ids = set()
        path = _data_path("checklists", "emergency_checklists.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for cl in data.get("checklists", []):
                        cid = cl.get("checklist_id")
                        if cid:
                            checklist_ids.add(cid)
            except Exception:
                pass

    for filename in ("airport_scenarios.json", "emergency_scenarios.json"):
        filepath = _data_path("scenarios", filename)
        if not os.path.exists(filepath):
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for s in data.get("scenarios", []):
                sid = s.get("scenario_id", "?")
                icao = (s.get("airport_icao") or "").upper()
                if icao and airport_icaos and icao not in airport_icaos:
                    results.append(ValidationResult(
                        entity_id=sid,
                        category="scenarios",
                        severity=Severity.ERROR,
                        message=f"airport_icao '{s.get('airport_icao')}' not found in airport_info.json",
                    ))
                else:
                    results.append(ValidationResult(
                        entity_id=sid,
                        category="scenarios",
                        severity=Severity.PASS,
                        message="OK" if not icao or icao in airport_icaos else "OK",
                    ))
                cid = s.get("checklist_id")
                if cid and checklist_ids and cid not in checklist_ids:
                    results.append(ValidationResult(
                        entity_id=sid,
                        category="scenarios",
                        severity=Severity.ERROR,
                        message=f"checklist_id '{cid}' not found in emergency_checklists.json",
                    ))
                elif cid:
                    results.append(ValidationResult(
                        entity_id=f"{sid} (checklist)",
                        category="scenarios",
                        severity=Severity.PASS,
                        message="Checklist reference OK",
                    ))
        except json.JSONDecodeError as e:
            results.append(ValidationResult(
                entity_id=filename,
                category="scenarios",
                severity=Severity.ERROR,
                message="Invalid JSON",
                detail=str(e),
            ))
        except Exception as e:
            results.append(ValidationResult(
                entity_id=filename,
                category="scenarios",
                severity=Severity.ERROR,
                message="Read error",
                detail=str(e),
            ))


def validate_checklists_structural(results: List[ValidationResult]) -> None:
    """Structural checks for emergency_checklists.json."""
    path = _data_path("checklists", "emergency_checklists.json")
    if not os.path.exists(path):
        results.append(ValidationResult(
            entity_id="emergency_checklists.json",
            category="checklists",
            severity=Severity.WARNING,
            message="File not found",
            detail=path,
        ))
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for cl in data.get("checklists", []):
            cid = cl.get("checklist_id")
            if not cid:
                results.append(ValidationResult(
                    entity_id=cl.get("name", "?"),
                    category="checklists",
                    severity=Severity.ERROR,
                    message="Checklist missing checklist_id",
                ))
            else:
                results.append(ValidationResult(
                    entity_id=cid,
                    category="checklists",
                    severity=Severity.PASS,
                    message="OK",
                ))
    except json.JSONDecodeError as e:
        results.append(ValidationResult(
            entity_id="emergency_checklists.json",
            category="checklists",
            severity=Severity.ERROR,
            message="Invalid JSON",
            detail=str(e),
        ))


def validate_training_records_structural(results: List[ValidationResult]) -> None:
    """Structural checks for session and pilot JSON in training_records."""
    path = _data_path("training_records")
    if not os.path.exists(path):
        return
    for filename in os.listdir(path):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(path, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            results.append(ValidationResult(
                entity_id=filename,
                category="training_records",
                severity=Severity.ERROR,
                message="Invalid JSON or read error",
                detail=str(e),
            ))
            continue
        if filename.startswith("session_"):
            if "session_id" not in data:
                results.append(ValidationResult(
                    entity_id=filename,
                    category="training_records",
                    severity=Severity.ERROR,
                    message="Missing session_id",
                ))
            else:
                results.append(ValidationResult(
                    entity_id=data.get("session_id", filename),
                    category="training_records",
                    severity=Severity.PASS,
                    message="OK",
                ))
        elif filename.startswith("pilot_"):
            if "pilot_id" not in data:
                results.append(ValidationResult(
                    entity_id=filename,
                    category="training_records",
                    severity=Severity.ERROR,
                    message="Missing pilot_id",
                ))
            else:
                results.append(ValidationResult(
                    entity_id=data.get("pilot_id", filename),
                    category="training_records",
                    severity=Severity.PASS,
                    message="OK",
                ))


def _ollama_available(base_url: str, timeout: int = 5) -> bool:
    try:
        r = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def _ollama_validate_snippet(
    base_url: str,
    model: str,
    category: str,
    entity_id: str,
    snippet: str,
    question: str,
    timeout: int = 25,
) -> Optional[str]:
    """Call Ollama to validate a snippet. Returns AI response text or None on failure."""
    system_prompt = """You are an ATC/phraseology and aviation procedure expert. Check the given data for correctness and consistency. Reply with exactly one line: PASS, WARN, or FAIL, then a short reason (e.g. "PASS - phraseology appropriate" or "WARN - visibility units inconsistent"). Be concise."""
    user_prompt = f"Category: {category}\nEntity: {entity_id}\n\nData:\n{snippet}\n\nQuestion: {question}\n\nReply (PASS/WARN/FAIL + reason):"
    try:
        payload = {
            "model": model,
            "prompt": user_prompt,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 150},
        }
        r = requests.post(
            f"{base_url.rstrip('/')}/api/generate",
            json=payload,
            timeout=timeout,
        )
        if r.status_code != 200:
            return None
        out = r.json().get("response", "").strip()
        return out if out else None
    except Exception:
        return None


def run_validation(
    scope: Dict[str, bool],
    structural_only: bool,
    config: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> List[ValidationResult]:
    """
    Run validation. scope keys: airports, scenarios, checklists, training_records.
    If structural_only is False and config has ollama_url and ai_model, run AI checks too.
    progress_callback(message) is called with status strings.
    """
    results: List[ValidationResult] = []
    config = config or {}
    ollama_url = config.get("ollama_url", "http://localhost:11434")
    model = config.get("ai_model", "llama2")
    use_ai = not structural_only and _ollama_available(ollama_url)

    if scope.get("airports", True):
        if progress_callback:
            progress_callback("Validating airports...")
        validate_airports_structural(results)

    if scope.get("scenarios", True):
        if progress_callback:
            progress_callback("Validating scenarios...")
        validate_scenarios_structural(results)

    if scope.get("checklists", True):
        if progress_callback:
            progress_callback("Validating checklists...")
        validate_checklists_structural(results)

    if scope.get("training_records", True):
        if progress_callback:
            progress_callback("Validating training records...")
        validate_training_records_structural(results)

    if use_ai and scope.get("scenarios", True):
        if progress_callback:
            progress_callback("Running AI validation on scenarios...")
        try:
            from data.scenarios.scenario_engine import ScenarioEngine
            engine = ScenarioEngine()
            all_scenarios = engine.get_all_scenarios()
            for i, scenario in enumerate(all_scenarios):
                if progress_callback and (i % 3 == 0):
                    progress_callback(f"Validating scenarios (AI) {i + 1}/{len(all_scenarios)}...")
                snippet = json.dumps({
                    "name": scenario.name,
                    "difficulty": scenario.difficulty.value,
                    "scenario_type": scenario.scenario_type.value,
                    "objectives": scenario.objectives[:5],
                    "expected_communications": scenario.expected_communications[:5],
                }, indent=0)
                ai_response = _ollama_validate_snippet(
                    ollama_url,
                    model,
                    "scenarios",
                    scenario.scenario_id,
                    snippet,
                    "Are objectives and expected_communications consistent with scenario type and difficulty?",
                )
                if ai_response:
                    upper = ai_response.upper()
                    if "FAIL" in upper:
                        results.append(ValidationResult(
                            entity_id=scenario.scenario_id,
                            category="scenarios",
                            severity=Severity.ERROR,
                            message="AI validation failed",
                            detail=ai_response,
                        ))
                    elif "WARN" in upper:
                        results.append(ValidationResult(
                            entity_id=scenario.scenario_id,
                            category="scenarios",
                            severity=Severity.WARNING,
                            message="AI validation warning",
                            detail=ai_response,
                        ))
                    else:
                        results.append(ValidationResult(
                            entity_id=scenario.scenario_id,
                            category="scenarios",
                            severity=Severity.PASS,
                            message="AI validation passed",
                            detail=ai_response,
                        ))
        except Exception as e:
            results.append(ValidationResult(
                entity_id="scenarios (AI)",
                category="scenarios",
                severity=Severity.WARNING,
                message="AI validation skipped",
                detail=str(e),
            ))

    if progress_callback:
        progress_callback("Validation complete.")
    return results
