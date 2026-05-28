import uuid
import enum

from sqlalchemy import Column, String, Enum, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    organizer = "organizer"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    firebase_uid = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)

    name = Column(String, nullable=False)
    organization = Column(String, nullable=True)

    role = Column(
        Enum(UserRole),
        default=UserRole.organizer,
        nullable=False
    )

    is_active = Column(Boolean, default=True)

    last_login = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now()
    )

    # Relationships
    events = relationship(
        "Event",
        back_populates="organizer",
        cascade="all, delete-orphan"
    )