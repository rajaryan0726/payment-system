from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.refund import Refund


class RefundRepository:
    @staticmethod
    def get_by_id(db: Session, refund_id: str) -> Optional[Refund]:
        return db.query(Refund).filter(Refund.id == refund_id).first()

    @staticmethod
    def get_by_idempotency(
        db: Session, payment_id: str, idempotency_key: str
    ) -> Optional[Refund]:
        return db.query(Refund).filter(
            Refund.payment_id == payment_id,
            Refund.idempotency_key == idempotency_key,
        ).first()

    @staticmethod
    def get_total_refunded_minor(db: Session, payment_id: str) -> int:
        total = (
            db.query(func.coalesce(func.sum(Refund.amount_minor), 0))
            .filter(
                Refund.payment_id == payment_id,
                Refund.status.in_(["INITIATED", "SUCCEEDED"]),
            )
            .scalar()
        )
        return int(total)

    @staticmethod
    def create(
        db: Session,
        payment_id: str,
        amount_minor: int,
        currency: str,
        idempotency_key: str,
        provider_refund_id: Optional[str] = None,
        reason: Optional[str] = None,
        status: str = "INITIATED",
    ) -> Refund:
        refund = Refund(
            payment_id=payment_id,
            amount_minor=amount_minor,
            currency=currency.upper(),
            idempotency_key=idempotency_key,
            provider_refund_id=provider_refund_id,
            reason=reason,
            status=status,
        )
        db.add(refund)
        db.commit()
        db.refresh(refund)
        return refund

    @staticmethod
    def update_status(
        db: Session, refund: Refund, status: str, provider_refund_id: Optional[str] = None
    ) -> Refund:
        refund.status = status
        if provider_refund_id:
            refund.provider_refund_id = provider_refund_id
        db.commit()
        db.refresh(refund)
        return refund
