from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String(10), nullable=False, default="user")
    created_at = Column(DateTime, default=datetime.utcnow)
    expenses = relationship("Expense", back_populates="owner", cascade="all, delete")


class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String(10), nullable=False, default="expense")  # "income" or "expense"
    category = Column(String(50), nullable=True)
    date = Column(Date, nullable=False)
    note = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="expenses")
