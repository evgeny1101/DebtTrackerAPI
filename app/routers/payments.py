from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import schemas
from app.dependencies import get_db, get_current_user
from app.models import User
from app.crud import payments as crud

router = APIRouter(prefix="/api", tags=["payments"])


@router.get("/payments", response_model=list[schemas.PaymentResponse])
def list_all_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.get_all_payments(db, current_user.id)


@router.get(
    "/debts/{debt_id}/payments",
    response_model=list[schemas.PaymentResponse],
)
def list_payments_for_debt(
    debt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.get_payments_for_debt(db, debt_id, current_user.id)


@router.post(
    "/debts/{debt_id}/payments",
    response_model=schemas.PaymentResponse,
    status_code=201,
)
def record_payment(
    debt_id: int,
    data: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.record_payment(db, debt_id, current_user.id, data)


@router.delete(
    "/debts/{debt_id}/payments/{payment_id}",
    response_model=schemas.PaymentDeleteResponse,
)
def delete_payment(
    debt_id: int,
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.delete_payment(db, debt_id, payment_id, current_user.id)
