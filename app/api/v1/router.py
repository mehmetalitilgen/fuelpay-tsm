from fastapi import APIRouter

from app.api.v1 import stations, terminals

router = APIRouter(prefix="/api/v1")
router.include_router(stations.router)
router.include_router(terminals.router)
