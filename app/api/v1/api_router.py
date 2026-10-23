from fastapi import APIRouter
from app.api.v1.admin import router as admin_router
from app.api.v1.health import router as health_router
from app.api.v1.payments import router as payments_router
from app.api.v1.refunds import router as refunds_router
from app.api.v1.webhooks import router as webhooks_router

api_v1_router = APIRouter()

# Health endpoints mounted at root and v1
api_v1_router.include_router(health_router)
api_v1_router.include_router(payments_router)
api_v1_router.include_router(refunds_router)
api_v1_router.include_router(webhooks_router)
api_v1_router.include_router(admin_router)
