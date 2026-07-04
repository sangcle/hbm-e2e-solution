from fastapi import APIRouter

from backend.app.domain.versions import API_VERSION, FORMULA_VERSION, MODEL_VERSION, PRESET_VERSION, SCHEMA_VERSION

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "schema_version": SCHEMA_VERSION,
        "api_version": API_VERSION,
        "model_version": MODEL_VERSION,
        "formula_version": FORMULA_VERSION,
        "preset_version": PRESET_VERSION,
    }
