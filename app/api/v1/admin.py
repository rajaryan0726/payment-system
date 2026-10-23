from typing import List, Tuple
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.deps import get_admin_authenticated
from app.core.exceptions import PaymentServiceException
from app.core.security import generate_client_credentials
from app.models.base import get_db
from app.models.client import ClientApplication
from app.models.payment import Payment, PaymentStatus
from app.providers.factory import get_payment_provider
from app.repositories.client_repo import ClientRepository
from app.repositories.payment_repo import PaymentRepository
from app.schemas.client import (
    ClientCredentialResponse,
    ClientRegisterRequest,
    ClientResponse,
)

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.post(
    "/clients",
    response_model=Tuple[ClientResponse, ClientCredentialResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register Client Application & Issue Credentials",
)
def register_client(
    request: ClientRegisterRequest,
    authenticated: bool = Depends(get_admin_authenticated),
    db: Session = Depends(get_db),
):
    """
    Onboards a new client system (such as AIAIC), registers its application ID,
    and returns initial API key credentials.
    """
    existing = ClientRepository.get_by_code(db, request.client_code)
    if existing:
        raise PaymentServiceException(
            status_code=status.HTTP_409_CONFLICT,
            error_code="CLIENT_ALREADY_EXISTS",
            message=f"Client application with code '{request.client_code}' already exists.",
        )

    client = ClientRepository.create_client(
        db=db, client_code=request.client_code, display_name=request.display_name
    )

    key_id, plaintext_secret, secret_hash = generate_client_credentials(is_test=True)
    cred = ClientRepository.create_credential(
        db=db, client_id=client.id, key_id=key_id, secret_hash=secret_hash
    )

    client_res = ClientResponse(
        id=client.id,
        client_code=client.client_code,
        display_name=client.display_name,
        status=client.status,
        created_at=client.created_at,
    )
    cred_res = ClientCredentialResponse(
        key_id=cred.key_id,
        client_secret=plaintext_secret,
        status=cred.status,
        created_at=cred.created_at,
    )
    return client_res, cred_res


@router.get(
    "/clients",
    response_model=List[ClientResponse],
    summary="List Registered Clients",
)
def list_clients(
    authenticated: bool = Depends(get_admin_authenticated),
    db: Session = Depends(get_db),
) -> List[ClientResponse]:
    """Lists all registered client applications."""
    clients = db.query(ClientApplication).all()
    return [
        ClientResponse(
            id=c.id,
            client_code=c.client_code,
            display_name=c.display_name,
            status=c.status,
            created_at=c.created_at,
        )
        for c in clients
    ]


@router.post(
    "/reconciliation-runs",
    summary="Trigger Provider Reconciliation",
)
async def run_reconciliation(
    authenticated: bool = Depends(get_admin_authenticated),
    db: Session = Depends(get_db),
):
    """
    Scans for transactions in PENDING or REQUIRES_RECONCILIATION status,
    cross-references them against Razorpay API records, and synchronizes status.
    """
    provider = get_payment_provider()
    pending_payments = (
        db.query(Payment)
        .filter(Payment.status.in_([PaymentStatus.PENDING.value, PaymentStatus.REQUIRES_RECONCILIATION.value]))
        .all()
    )

    reconciled_count = 0
    results = []

    for payment in pending_payments:
        if not payment.provider_order_id:
            continue
        try:
            order_data = await provider.fetch_order(payment.provider_order_id)
            order_status = order_data.get("status")

            if order_status == "paid":
                # Order is paid, transition to SUCCEEDED
                PaymentRepository.transition_status(
                    db=db,
                    payment=payment,
                    new_status=PaymentStatus.SUCCEEDED.value,
                    source="RECONCILIATION",
                    event_type="RECONCILIATION_SYNCED",
                    provider_status=order_status,
                )
                reconciled_count += 1
                results.append({"payment_id": payment.id, "action": "TRANSITIONED_TO_SUCCEEDED"})
        except Exception as e:
            results.append({"payment_id": payment.id, "error": str(e)})

    return {
        "status": "completed",
        "scanned": len(pending_payments),
        "reconciled": reconciled_count,
        "results": results,
    }
