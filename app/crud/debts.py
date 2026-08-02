import logging
import time

from sqlalchemy.orm import Session

from app.models import Debt
from app.schemas import DebtCreate, DebtUpdate

logger = logging.getLogger(__name__)


def get_debts(db: Session, user_id: int, active_only: bool = False):
    query = db.query(Debt).filter(Debt.userId == user_id)
    if active_only:
        query = query.filter(Debt.currentAmount != 0)
    return query.all()


def get_debt(db: Session, debt_id: int, user_id: int):
    return db.query(Debt).filter(Debt.id == debt_id, Debt.userId == user_id).first()


def get_debts_with_reminders(db: Session, user_id: int):
    return (
        db.query(Debt)
        .filter(
            Debt.userId == user_id,
            Debt.reminderIntervalDays.isnot(None),
        )
        .all()
    )


def create_debt(db: Session, user_id: int, data: DebtCreate) -> Debt:
    now = int(time.time() * 1000)
    debt = Debt(
        name=data.name,
        type=data.debtType.value,
        initialAmount=data.initialAmount,
        currentAmount=data.initialAmount,
        createdAt=data.createdAt or now,
        reminderIntervalDays=data.reminderIntervalDays,
        userId=user_id,
    )
    db.add(debt)
    db.commit()
    db.refresh(debt)
    logger.info("Debt created: id=%d name=%s initial=%d", debt.id, debt.name, debt.initialAmount)
    return debt


def update_debt(db: Session, debt_id: int, user_id: int, data: DebtUpdate) -> Debt | None:
    debt = get_debt(db, debt_id, user_id)
    if not debt:
        return None

    old_initial = debt.initialAmount
    old_current = debt.currentAmount
    paid = max(0, old_initial - old_current) if old_initial > 0 else 0

    new_initial = data.initialAmount
    new_current = max(0, new_initial - paid)

    now = int(time.time() * 1000)
    debt.name = data.name
    debt.initialAmount = new_initial
    debt.currentAmount = new_current
    debt.createdAt = data.createdAt or now
    debt.reminderIntervalDays = data.reminderIntervalDays

    db.commit()
    db.refresh(debt)
    logger.info(
        "Debt updated: id=%d initial=%d->%d current=%d",
        debt.id,
        old_initial,
        new_initial,
        new_current,
    )
    return debt


def update_current_amount(db: Session, debt_id: int, user_id: int, amount: int) -> Debt | None:
    debt = get_debt(db, debt_id, user_id)
    if not debt:
        return None
    debt.currentAmount = amount
    db.commit()
    db.refresh(debt)
    return debt


def update_reminder_timestamp(
    db: Session, debt_id: int, user_id: int, timestamp: int
) -> Debt | None:
    debt = get_debt(db, debt_id, user_id)
    if not debt:
        return None
    debt.lastReminderTimestamp = timestamp
    db.commit()
    db.refresh(debt)
    return debt


def delete_debt(db: Session, debt_id: int, user_id: int) -> bool:
    debt = get_debt(db, debt_id, user_id)
    if not debt:
        logger.warning("Debt delete failed: id=%d not found", debt_id)
        return False
    db.delete(debt)
    db.commit()
    logger.info("Debt deleted: id=%d", debt_id)
    return True
