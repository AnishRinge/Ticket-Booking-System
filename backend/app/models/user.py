import enum
from sqlalchemy import Column, Integer, String, Enum
from .base import Base, TimestampMixin

class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    ORGANISER = "ORGANISER"
    ADMIN = "ADMIN"

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER, nullable=False)
