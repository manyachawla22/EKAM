import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint

from app.core.database import Base


class Theme(Base):
    __tablename__ = "themes"

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "name",
            name="uq_event_theme_name"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("events.id"),
        nullable=False
    )

    name = Column(String, nullable=False)

    description = Column(Text, nullable=True)

    required_skills = Column(ARRAY(String), default=[])

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    event = relationship("Event", back_populates="themes")

    teams = relationship(
        "Team",
        back_populates="theme"
    )