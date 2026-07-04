from fastapi import APIRouter

from backend.app.presets.preset_registry import all_presets

router = APIRouter(tags=["presets"])


@router.get("/presets")
def presets():
    return all_presets()
