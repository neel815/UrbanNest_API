import logging
from datetime import date

from app.database import SessionLocal
from app.models.resident import Payment, PaymentStatus

logger = logging.getLogger(__name__)


def mark_overdue_payments() -> None:
    db = SessionLocal()
    try:
        overdue_payments = (
            db.query(Payment)
            .filter(
                Payment.status == PaymentStatus.PENDING,
                Payment.due_date < date.today(),
            )
            .all()
        )

        for payment in overdue_payments:
            payment.status = PaymentStatus.OVERDUE

        db.commit()
        logger.info(f"Overdue job ran: marked {len(overdue_payments)} payments as overdue")
    except Exception as e:  # pragma: no cover - safety logging path
        logger.error(f"Overdue job failed: {e}")
        db.rollback()
    finally:
        db.close()