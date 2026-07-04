from fastapi import APIRouter

from backend.app.backends.ramulator2.status import ramulator2_status

router = APIRouter(tags=["backends"])


@router.get("/backends/ramulator2/status")
def get_ramulator2_status():
    return ramulator2_status()
