from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, constr


class ClientRegisterRequest(BaseModel):
    client_code: str = Field(..., min_length=3, max_length=64, description="Unique identifier for client application, e.g. aiaic-farm-to-retail")
    display_name: str = Field(..., min_length=3, max_length=128, description="Human readable application title")


class ClientCredentialResponse(BaseModel):
    key_id: str
    client_secret: str = Field(..., description="Plaintext secret. Save immediately; will never be shown again.")
    status: str
    created_at: datetime


class ClientResponse(BaseModel):
    id: str
    client_code: str
    display_name: str
    status: str
    created_at: datetime
