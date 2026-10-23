from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_authenticated_client
from app.models.base import get_db
from app.models.client import ClientApplication
from app.repositories.payment_repo import PaymentRepository
from app.schemas.payment import (
    PaymentCreateRequest,
    PaymentResponse,
    PaymentStatusResponse,
    PaymentVerifyRequest,
)
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])
payment_service = PaymentService()


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Payment & Provider Order",
)
def create_payment(
    request: PaymentCreateRequest,
    client: ClientApplication = Depends(get_authenticated_client),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    """
    Creates an internal payment record, initializes a provider-side order on Razorpay,
    and returns checkout launch information for client frontends.
    """
    return payment_service.create_payment(db=db, client=client, request=request)


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="Get Payment Details",
)
def get_payment(
    payment_id: str,
    client: ClientApplication = Depends(get_authenticated_client),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    """Retrieves full details of a payment owned by the calling client."""
    return payment_service.get_payment(db=db, client=client, payment_id=payment_id)


@router.get(
    "/{payment_id}/status",
    response_model=PaymentStatusResponse,
    summary="Get Normalized Status",
)
def get_payment_status(
    payment_id: str,
    client: ClientApplication = Depends(get_authenticated_client),
    db: Session = Depends(get_db),
) -> PaymentStatusResponse:
    """Returns lightweight normalized status for client polling and workflow progression."""
    payment_resp = payment_service.get_payment(db=db, client=client, payment_id=payment_id)
    return PaymentStatusResponse(
        id=payment_resp.id,
        business_reference=payment_resp.business_reference,
        status=payment_resp.status,
        provider_status=payment_resp.provider_status,
        amount_minor=payment_resp.amount_minor,
        currency=payment_resp.currency,
        verified_at=payment_resp.verified_at,
        created_at=payment_resp.created_at,
    )


@router.post(
    "/{payment_id}/verify",
    response_model=PaymentResponse,
    summary="Verify Checkout Result",
)
def verify_payment(
    payment_id: str,
    request: PaymentVerifyRequest,
    client: ClientApplication = Depends(get_authenticated_client),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    """
    Cryptographically verifies the Razorpay signature and checks authoritative
    provider status before transitioning payment to SUCCEEDED.
    """
    return payment_service.verify_payment(
        db=db, client=client, payment_id=payment_id, request=request
    )


@router.get(
    "",
    response_model=List[PaymentResponse],
    summary="List Client Payments",
)
def list_payments(
    status: Optional[str] = Query(default=None, description="Filter by PaymentStatus"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    client: ClientApplication = Depends(get_authenticated_client),
    db: Session = Depends(get_db),
) -> List[PaymentResponse]:
    """Lists payments created by the authenticated client with controlled pagination."""
    payments = PaymentRepository.list_by_client(
        db=db, client_id=client.id, limit=limit, offset=offset, status=status
    )
    return [payment_service._to_response(p) for p in payments]
