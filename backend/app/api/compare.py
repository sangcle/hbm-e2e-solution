from fastapi import APIRouter, HTTPException

from backend.app.api.dependencies import simulation_service
from backend.app.domain.candidate import CompareRequest

router = APIRouter(tags=["compare"])


@router.post("/compare")
def compare(request: CompareRequest):
    try:
        return simulation_service.compare(request)
    except KeyError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "UNKNOWN_PRESET", "message": str(exc), "details": {}},
        ) from exc
