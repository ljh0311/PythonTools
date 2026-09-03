"""CarRS local web API — recommendations for phone/laptop on the LAN."""

from __future__ import annotations

import os
import socket
from datetime import datetime
from functools import lru_cache
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# CarRS project root (parent of web/)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

if ROOT not in os.sys.path:
    os.sys.path.insert(0, ROOT)

from car_rental_recommender_core import (  # noqa: E402
    create_complete_cost_analysis,
    create_ml_budget_prediction,
    enhance_dataframe,
    get_ollama_enhanced_recommendations,
    load_data,
    predict_rental_possibility,
)
from components.ml_calibration import ensure_calibration, summarize_calibration  # noqa: E402

DEFAULT_CSV = os.path.join(ROOT, "22 - Sheet1.csv")

app = FastAPI(title="CarRS Web", version="1.0.0")


class RecommendBody(BaseModel):
    distance_km: float = Field(..., gt=0, le=5000)
    duration_hours: float = Field(..., gt=0, le=720)
    is_weekend: bool = False
    region: Literal["Singapore", "Malaysia"] = "Singapore"
    top_n: int = Field(default=8, ge=1, le=20)
    use_ml: bool = True


def _resolve_csv() -> str:
    env = os.environ.get("CARRS_CSV")
    if env and os.path.exists(env):
        return env
    if os.path.exists(DEFAULT_CSV):
        return DEFAULT_CSV
    raise FileNotFoundError(
        f"CSV not found: {DEFAULT_CSV}. Put rental history there or set CARRS_CSV."
    )


@lru_cache(maxsize=1)
def _load_bundle() -> tuple[Any, str, int]:
    path = _resolve_csv()
    df = enhance_dataframe(load_data(path))
    try:
        ensure_calibration(df)
    except Exception:
        pass
    return df, path, len(df)


def reload_data() -> dict[str, Any]:
    _load_bundle.cache_clear()
    df, path, n = _load_bundle()
    return {"csv": path, "rows": n}


def _lan_ips() -> list[str]:
    ips: list[str] = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except OSError:
        pass
    return ips


@app.get("/api/health")
def health() -> dict[str, Any]:
    try:
        _, path, rows = _load_bundle()
        return {
            "ok": True,
            "rows": rows,
            "csv": os.path.basename(path),
            "lan_urls": [f"http://{ip}:8765" for ip in _lan_ips()],
        }
    except FileNotFoundError as exc:
        return {"ok": False, "error": str(exc), "lan_urls": [f"http://{ip}:8765" for ip in _lan_ips()]}


@app.post("/api/reload")
def api_reload() -> dict[str, Any]:
    try:
        return {"ok": True, **reload_data()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/recommend")
def recommend(body: RecommendBody) -> dict[str, Any]:
    try:
        df, path, rows = _load_bundle()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    region_df = df
    if "Region" in df.columns:
        filtered = df[df["Region"].fillna("Singapore") == body.region]
        if len(filtered) >= 5:
            region_df = filtered

    cost_analysis = create_complete_cost_analysis(region_df, region=body.region)
    recs = get_ollama_enhanced_recommendations(
        body.distance_km,
        body.duration_hours,
        region_df,
        cost_analysis,
        body.is_weekend,
        top_n=body.top_n,
        use_ollama=False,
        use_ml=body.use_ml,
    )

    clean = []
    for r in recs:
        clean.append(
            {
                "provider": r.get("provider"),
                "model": r.get("model"),
                "total_cost": round(float(r.get("total_cost") or 0), 2),
                "method": r.get("method"),
                "confidence": r.get("confidence"),
                "calibration_factor": r.get("calibration_factor"),
                "rate_floor_applied": r.get("rate_floor_applied"),
                "raw_total_cost": (
                    round(float(r["raw_total_cost"]), 2)
                    if r.get("raw_total_cost") is not None
                    else None
                ),
            }
        )

    return {
        "distance_km": body.distance_km,
        "duration_hours": body.duration_hours,
        "is_weekend": body.is_weekend,
        "region": body.region,
        "rows_used": len(region_df),
        "csv": os.path.basename(path),
        "recommendations": clean,
    }


@app.get("/api/possibility")
def possibility(
    date: str = Query(..., description="YYYY-MM-DD"),
    distance_km: float = Query(40, gt=0),
    duration_hours: float = Query(1, gt=0),
    is_weekend: Optional[bool] = None,
) -> dict[str, Any]:
    try:
        df, _, _ = _load_bundle()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        target = datetime.strptime(date, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD") from exc

    weekend = is_weekend if is_weekend is not None else target.weekday() >= 5
    result = predict_rental_possibility(
        df,
        target,
        {"distance": distance_km, "duration": duration_hours, "is_weekend": weekend},
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {
        "date": date,
        "possibility_pct": result.get("possibility_percentage"),
        "method": result.get("method"),
        "recommended_provider": result.get("recommended_provider"),
    }


@app.get("/api/calibration")
def calibration() -> dict[str, Any]:
    try:
        df, _, _ = _load_bundle()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    cal = ensure_calibration(df)
    return summarize_calibration(cal)


@app.get("/api/budget")
def budget(limit: float = Query(500, gt=0)) -> dict[str, Any]:
    try:
        df, _, _ = _load_bundle()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        pred = create_ml_budget_prediction(df, limit, "next_month", "medium")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "predicted_spending": pred.get("predicted_spending"),
        "data_points": pred.get("data_points"),
        "budget_limit": limit,
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
