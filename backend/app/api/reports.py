from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from backend.app.api.dependencies import repository

router = APIRouter(tags=["reports"])


@router.get("/report/{run_id}", response_class=PlainTextResponse)
def get_report(run_id: str):
    try:
        return repository.load_report(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "RUN_NOT_FOUND", "message": f"Run not found: {run_id}", "details": {}},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "INVALID_RUN_ID", "message": str(exc), "details": {"run_id": run_id}},
        ) from exc
