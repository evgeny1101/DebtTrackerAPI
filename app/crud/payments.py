import time
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import Debt, Payment
from app.schemas import PaymentCreate


def record_payment(
    db: Session, debt_id: int, user_id: int, data: PaymentCreate
) -> Payment:
    debt = (
        db.query(Debt)
        .filter(Debt.id == debt_id, Debt.userId == user_id)
        .first()
    )
    if not debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debt not found")

    if debt.currentAmount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Долг уже полностью погашен",
        )

    now = int(time.time() * 1000)
    payment = Payment(
        amount=data.amount,
        dateMillis=data.dateMillis or now,
        debtId=debt_id,
    )
    db.add(payment)
    debt.currentAmount = max(0, debt.currentAmount - data.amount)
    db.commit()
    db.refresh(payment)
    return payment


def delete_payment(
    db: Session, debt_id: int, payment_id: int, user_id: int
) -> dict:
    debt = (
        db.query(Debt)
        .filter(Debt.id == debt_id, Debt.userId == user_id)
        .first()
    )
    payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id, Payment.debtId == debt_id)
        .first()
    )

    if not debt or not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debt or payment not found",
        )

    amount = payment.amount
    db.delete(payment)
    debt.currentAmount += amount
    db.commit()

    return {
        "id": payment_id,
        "amount": amount,
        "debtId": debt_id,
        "currentAmount": debt.currentAmount,
    }


def get_payments_for_debt(
    db: Session, debt_id: int, user_id: int
) -> list[Payment]:
    debt = (
        db.query(Debt)
        .filter(Debt.id == debt_id, Debt.userId == user_id)
        .first()
    )
    if not debt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Debt not found"
        )

    return (
        db.query(Payment)
        .filter(Payment.debtId == debt_id)
        .order_by(Payment.dateMillis.desc())
        .all()
    )


def get_all_payments(db: Session, user_id: int) -> list[Payment]:
    return (
        db.query(Payment)
        .join(Debt)
        .filter(Debt.userId == user_id)
        .order_by(Payment.dateMillis.desc())
        .all()
    )
