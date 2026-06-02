import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class EventPipeline(Base):
    """Tracks an event's position in its dynamic, per-round pipeline.

    `current_step` is a step id produced by pipeline_service.build_steps
    (e.g. "registration", "round:<uuid>:submission", "winner_announcement").
    `data` holds runtime markers: {"eliminated_team_ids": [...], "done_steps": [...]}.
    """

    __tablename__ = "event_pipeline"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    current_step = Column(String, nullable=False, default="registration")

    data = Column(JSONB, nullable=False, default=dict)

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
