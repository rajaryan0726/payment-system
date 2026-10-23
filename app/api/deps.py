import hmac
from typing import Generator, Optional
from fastapi import Depends, Header, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import verify_client_secret
from app.models.base import get_db
from app.models.client import ClientApplication
from app.repositories.client_repo import ClientRepository

client_id_header = APIKeyHeader(name="X-Client-Id", auto_error=False)
client_secret_header = APIKeyHeader(name="X-Client-Secret", auto_error=False)
admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def get_authenticated_client(
    key_id: Optional[str] = Security(client_id_header),
    client_secret: Optional[str] = Security(client_secret_header),
    db: Session = Depends(get_db),
) -> ClientApplication:
    """
    Authenticates client application using X-Client-Id and X-Client-Secret headers.
    Ensures that caller identity is cryptographically and securely verified.
    """
    if not key_id or not client_secret:
        raise AuthenticationError("Missing required authentication headers: X-Client-Id and X-Client-Secret")

    credential = ClientRepository.get_credential_by_key_id(db, key_id)
    if not credential or credential.status != "ACTIVE":
        raise AuthenticationError("Invalid or revoked client credentials")

    if not verify_client_secret(client_secret, credential.secret_hash):
        raise AuthenticationError("Invalid client secret")

    client = credential.client_application
    if not client or client.status != "ACTIVE":
        raise AuthorizationError("Client application is inactive or revoked")

    # Update last_used_at
    ClientRepository.update_last_used(db, credential.id)
    return client


def get_admin_authenticated(
    admin_key: Optional[str] = Security(admin_key_header),
) -> bool:
    """Verifies master administrative key for /admin endpoints."""
    if not admin_key or not hmac.compare_digest(admin_key, settings.ADMIN_API_KEY):
        raise AuthorizationError("Invalid or missing X-Admin-Key")
    return True
