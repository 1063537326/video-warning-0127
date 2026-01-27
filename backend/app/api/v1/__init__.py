# API V1 Routes
from fastapi import APIRouter

from app.api.v1 import auth, users, cameras, zones, persons, groups, alerts, settings, logs, stream

router = APIRouter()

# 注册所有子路由
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(cameras.router)
router.include_router(zones.router)
router.include_router(persons.router)
router.include_router(groups.router)
router.include_router(alerts.router)
router.include_router(settings.router)
router.include_router(logs.router)
router.include_router(stream.router, prefix="/stream", tags=["实时预览"])
