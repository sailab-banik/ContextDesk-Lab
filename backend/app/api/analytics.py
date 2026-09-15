"""Analytics routes: aggregates, request history, and single-request replay."""

from fastapi import APIRouter, HTTPException, Query

from app.api.dependencies import TelemetryServiceDep
from app.models.analytics import AnalyticsSummary, HistoryPage
from app.models.execution import ExecutionRecord

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def summary(telemetry: TelemetryServiceDep) -> AnalyticsSummary:
    """Latency, cache, LLM, and context metrics across recorded requests.

    Cost figures are estimates derived from token counts.
    """
    return telemetry.summary()


@router.get("/history", response_model=HistoryPage)
def history(telemetry: TelemetryServiceDep, limit: int = Query(25, ge=1, le=200)) -> HistoryPage:
    return telemetry.history(limit)


@router.get("/history/{request_id}", response_model=ExecutionRecord)
def replay(request_id: str, telemetry: TelemetryServiceDep) -> ExecutionRecord:
    """The full record behind one request: every step, in order, with what it
    contributed."""
    record = telemetry.get(request_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No execution record for {request_id}")
    return record
