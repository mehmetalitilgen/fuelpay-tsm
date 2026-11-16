from fastapi import APIRouter

from app.api.v1 import stations

router = APIRouter(prefix="/api/v1")
router.include_router(stations.router)
