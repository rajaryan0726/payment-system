from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.deps import get_authenticated_client
from app.models.base import get_db
from app.models.client import ClientApplication
from app.schemas.refund import RefundCreateRequest, RefundResponse
from app.services.refund_service import RefundService

router = APIRouter(tags=["Refunds"])
refund_service = RefundService()


@router.post(
    "/payments/{payment_id}/refunds",
    response_model=RefundResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate Refund",
)
def create_refund(
    payment_id: str,
    request: RefundCreateRequest,
    client: ClientApplication = Depends(get_authenticated_client),
    db: Session = Depends(get_db),
) -> RefundResponse:
    """
    Initiates an authorized full or partial refund for a SUCCEEDED payment.
    Validates remaining refundable balance and prevents duplicate refunds via idempotency.
    """
    return refund_service.initiate_refund(
        db=db, client=client, payment_id=payment_id, request=request
    )


@router.get(
    "/refunds/{refund_id}",
    response_model=RefundResponse,
    summary="Get Refund Status",
)
def get_refund(
    refund_id: str,
    client: ClientApplication = Depends(get_authenticated_client),
    db: Session = Depends(get_db),
) -> RefundResponse:
    """Retrieves refund details for an authorized client."""
    return refund_service.get_refund(db=db, client=client, refund_id=refund_id)
