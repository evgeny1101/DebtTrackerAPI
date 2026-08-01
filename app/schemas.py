from pydantic import BaseModel, ConfigDict, Field
from enum import Enum
from typing import Optional


class DebtType(str, Enum):
    I_OWE = "I_OWE"
    OWE_ME = "OWE_ME"


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    createdAt: int

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    accessToken: str
    refreshToken: str
    tokenType: str = "bearer"


class RefreshRequest(BaseModel):
    refreshToken: str


class DebtCreate(BaseModel):
    name: str
    debtType: DebtType
    initialAmount: int = Field(..., gt=0)
    createdAt: Optional[int] = None
    reminderIntervalDays: Optional[int] = None


class DebtUpdate(BaseModel):
    name: str
    initialAmount: int = Field(..., gt=0)
    createdAt: Optional[int] = None
    reminderIntervalDays: Optional[int] = None


class DebtUpdateCurrentAmount(BaseModel):
    amount: int = Field(..., ge=0)


class DebtUpdateReminderTimestamp(BaseModel):
    timestamp: int


class DebtResponse(BaseModel):
    id: int
    name: str
    type: DebtType
    initialAmount: int
    currentAmount: int
    createdAt: int
    reminderIntervalDays: Optional[int] = None
    lastReminderTimestamp: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class PaymentCreate(BaseModel):
    amount: int = Field(..., gt=0)
    dateMillis: Optional[int] = None


class PaymentResponse(BaseModel):
    id: int
    amount: int
    dateMillis: int
    debtId: int

    model_config = ConfigDict(from_attributes=True)


class PaymentDeleteResponse(BaseModel):
    id: int
    amount: int
    debtId: int
    currentAmount: int
