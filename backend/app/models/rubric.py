import uuid

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class RubricCriterion(Base):
    """A single scoring criterion within a round's rubric.

    Judges score each criterion up to `max_score`; the evaluation's total is
    the sum of the criterion scores.
    """

    __tablename__ = "rubric_criteria"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    round_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String, nullable=False)

    description = Column(Text, nullable=True)

    max_score = Column(Float, nullable=False, default=10.0)

    position = Column(Integer, nullable=False, default=0)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
