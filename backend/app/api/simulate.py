from fastapi import APIRouter, HTTPException

from backend.app.api.dependencies import repository, simulation_service
from backend.app.domain.candidate import SimulateRequest

router = APIRouter(tags=["simulate"])


@router.post("/concept/evaluate")
def evaluate(request: SimulateRequest):
    try:
        return simulation_service.run(request, persist=False)
    except KeyError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "UNKNOWN_PRESET", "message": str(exc), "details": {}},
        ) from exc


@router.post("/simulate/run")
def run_simulation(request: SimulateRequest):
    try:
        return simulation_service.run(request, persist=True)
    except KeyError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "UNKNOWN_PRESET", "message": str(exc), "details": {}},
        ) from exc


@router.get("/simulate/result/{run_id}")
def get_result(run_id: str):
    try:
        return repository.load_result(run_id)
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
