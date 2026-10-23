import time
import uuid
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.api_router import api_v1_router
from app.api.v1.health import router as root_health_router
from app.core.config import settings
from app.core.exceptions import PaymentServiceException
from app.core.logging import logger


def create_application() -> FastAPI:
    """FastAPI application factory for BHIV Central Payment Service."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Standalone, reusable, multi-tenant payment infrastructure for the BHIV ecosystem.",
        docs_url="/docs" if not settings.is_production or settings.DEBUG else None,
        redoc_url="/redoc" if not settings.is_production or settings.DEBUG else None,
        openapi_url="/openapi.json" if not settings.is_production or settings.DEBUG else None,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.DEBUG else ["https://bhiv.io"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID and correlation logging middleware
    @app.middleware("http")
    async def request_correlation_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.time()

        try:
            response = await call_next(request)
            duration = round((time.time() - start_time) * 1000, 2)
            response.headers["X-Request-ID"] = request_id
            logger.info(
                f"{request.method} {request.url.path} responded {response.status_code} in {duration}ms",
                extra={"request_id": request_id},
            )
            return response
        except Exception as exc:
            duration = round((time.time() - start_time) * 1000, 2)
            logger.error(
                f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}",
                exc_info=True,
                extra={"request_id": request_id},
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred while processing the request.",
                        "request_id": request_id,
                    }
                },
                headers={"X-Request-ID": request_id},
            )

    # Custom exception handler for structured domain exceptions
    @app.exception_handler(PaymentServiceException)
    async def domain_exception_handler(request: Request, exc: PaymentServiceException):
        request_id = request.headers.get("X-Request-ID", "req_unknown")
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
            headers={"X-Request-ID": request_id},
        )

    # Mount routes
    app.include_router(root_health_router)  # Mounted at root /health & /ready
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_application()
