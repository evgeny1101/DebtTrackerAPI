from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import schemas
from app.config import api_path_prefix
from app.crud import debts as crud
from app.dependencies import get_current_user, get_db
from app.models import User

router = APIRouter(prefix=f"{api_path_prefix()}/api/debts", tags=["debts"])


@router.get("", response_model=list[schemas.DebtResponse])
def list_debts(
    active: bool | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.get_debts(db, current_user.id, active_only=(active is True))


@router.get("/with-reminders", response_model=list[schemas.DebtResponse])
def list_debts_with_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.get_debts_with_reminders(db, current_user.id)


@router.get("/{debt_id}", response_model=schemas.DebtResponse)
def get_debt(
    debt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    debt = crud.get_debt(db, debt_id, current_user.id)
    if not debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debt not found")
    return debt


@router.post("", response_model=schemas.DebtResponse, status_code=201)
def create_debt(
    data: schemas.DebtCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud.create_debt(db, current_user.id, data)


@router.put("/{debt_id}", response_model=schemas.DebtResponse)
def update_debt(
    debt_id: int,
    data: schemas.DebtUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    debt = crud.update_debt(db, debt_id, current_user.id, data)
    if not debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debt not found")
    return debt


@router.patch("/{debt_id}/current-amount", response_model=schemas.DebtResponse)
def patch_current_amount(
    debt_id: int,
    data: schemas.DebtUpdateCurrentAmount,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    debt = crud.update_current_amount(db, debt_id, current_user.id, data.amount)
    if not debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debt not found")
    return debt


@router.patch("/{debt_id}/reminder-timestamp", response_model=schemas.DebtResponse)
def patch_reminder_timestamp(
    debt_id: int,
    data: schemas.DebtUpdateReminderTimestamp,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    debt = crud.update_reminder_timestamp(db, debt_id, current_user.id, data.timestamp)
    if not debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debt not found")
    return debt


@router.delete("/{debt_id}", status_code=204)
def delete_debt(
    debt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = crud.delete_debt(db, debt_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debt not found")
    return None
