from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from backend.app.api.dependencies import repository

router = APIRouter(tags=["runs"])


@router.get("/runs")
def list_runs():
    return {"runs": repository.list_runs()}


@router.get("/runs/{run_id}/status")
def run_status(run_id: str):
    result = repository.load_result(run_id)
    metadata = result.get("metadata", {})
    return {
        "run_id": run_id,
        "status": metadata.get("status", "completed"),
        "created_at": metadata.get("created_at"),
    }


@router.get("/runs/{run_id}/artifacts")
def list_backend_artifacts(run_id: str):
    try:
        return {"run_id": run_id, "artifacts": repository.list_backend_artifacts(run_id)}
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "INVALID_RUN_ID", "message": str(exc), "details": {"run_id": run_id}},
        ) from exc


@router.get("/runs/{run_id}/artifacts/{artifact_path:path}", response_class=PlainTextResponse)
def get_backend_artifact(run_id: str, artifact_path: str):
    try:
        content, _ = repository.load_backend_artifact(run_id, artifact_path)
        return content
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "ARTIFACT_NOT_FOUND",
                "message": f"Artifact not found: {artifact_path}",
                "details": {"run_id": run_id, "artifact_path": artifact_path},
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_ARTIFACT_PATH",
                "message": str(exc),
                "details": {"run_id": run_id, "artifact_path": artifact_path},
            },
        ) from exc
