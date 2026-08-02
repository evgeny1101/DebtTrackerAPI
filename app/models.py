from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True, index=True)
    passwordHash = Column(String, nullable=False)
    createdAt = Column(BigInteger, nullable=False)

    debts = relationship("Debt", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String, nullable=False, unique=True, index=True)
    userId = Column(Integer, ForeignKey("users.id"), nullable=False)
    expiresAt = Column(BigInteger, nullable=False)
    createdAt = Column(BigInteger, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")


class Debt(Base):
    __tablename__ = "debts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    initialAmount = Column(BigInteger, nullable=False)
    currentAmount = Column(BigInteger, nullable=False)
    createdAt = Column(BigInteger, nullable=False)
    reminderIntervalDays = Column(Integer, nullable=True)
    lastReminderTimestamp = Column(BigInteger, nullable=True)
    userId = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="debts")
    payments = relationship("Payment", back_populates="debt", cascade="all, delete-orphan")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    amount = Column(BigInteger, nullable=False)
    dateMillis = Column(BigInteger, nullable=False)
    debtId = Column(Integer, ForeignKey("debts.id"), nullable=False)

    debt = relationship("Debt", back_populates="payments")
