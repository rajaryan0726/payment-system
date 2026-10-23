from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable explanation")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Contextual error metadata")


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str


class ReadyResponse(BaseModel):
    status: str = "ready"
    database: str = "connected"
    provider: str
