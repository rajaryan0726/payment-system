from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.orm import Session
from app.models.base import get_db
from app.schemas.webhook import WebhookAck
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
webhook_service = WebhookService()


@router.post(
    "/razorpay",
    response_model=WebhookAck,
    status_code=status.HTTP_200_OK,
    summary="Receive Razorpay Webhooks",
)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None, alias="X-Razorpay-Signature"),
    db: Session = Depends(get_db),
) -> WebhookAck:
    """
    Dedicated webhook endpoint for Razorpay asynchronous payment events.
    Verifies raw body signature, deduplicates event IDs, and applies state machine transitions.
    """
    raw_body = await request.body()
    return webhook_service.process_razorpay_webhook(
        db=db, raw_body=raw_body, signature_header=x_razorpay_signature
    )
