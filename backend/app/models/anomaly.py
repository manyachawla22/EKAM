import uuid
from datetime import datetime
import enum

from sqlalchemy import (
    Column,
    String,
    Float,
    DateTime,
    ForeignKey,
    Enum,
    Boolean
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class AnomalyType(str, enum.Enum):
    score_variance = "score_variance"
    bias_detected = "bias_detected"
    time_anomaly = "time_anomaly"


class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    evaluation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("evaluations.id", ondelete="CASCADE"),
        nullable=False
    )
    
    anomaly_type = Column(
        Enum(AnomalyType),
        nullable=False,
        index=True
    )
    
    severity = Column(
        Float,  # 0.0 to 1.0 score
        nullable=False
    )
    
    description = Column(
        String,
        nullable=False
    )
    
    is_resolved = Column(
        Boolean,
        default=False,
        nullable=False
    )
    
    resolved_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    resolved_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    event = relationship("Event", backref="anomalies")
    evaluation = relationship("Evaluation", backref="anomalies")
