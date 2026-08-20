from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


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
    name: str = Field(..., min_length=1, max_length=200)
    debtType: DebtType
    initialAmount: int = Field(..., gt=0)
    createdAt: int | None = None
    reminderIntervalDays: int | None = Field(default=None, gt=0)


class DebtUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    initialAmount: int = Field(..., gt=0)
    createdAt: int | None = None
    reminderIntervalDays: int | None = Field(default=None, gt=0)


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
    reminderIntervalDays: int | None = None
    lastReminderTimestamp: int | None = None

    model_config = ConfigDict(from_attributes=True)


class PaymentCreate(BaseModel):
    amount: int = Field(..., gt=0)
    dateMillis: int | None = None


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
