"""
EKAM Match model (Task 3, Stage 5c — Tournament Bracket).

A single-elimination knockout match between two contestants (teams; a team is the
generic "entry", so for individual events it's the participant's singleton team —
§7b.3). The bracket is a tree of these: a match's winner is promoted into a
`next_match` slot, so recording results advances the tree. Empty later-round slots
are created up front (sides NULL = "TBD") and fill in as winners are decided.
"""

import uuid

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Match(Base):
    __tablename__ = "matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    round_id = Column(UUID(as_uuid=True), ForeignKey("rounds.id", ondelete="CASCADE"), nullable=True, index=True)

    # Position in the knockout tree. round_number 1 = first round; increases toward
    # the final. match_index = 0-based position within that bracket round.
    round_number = Column(Integer, nullable=False, default=1)
    match_index = Column(Integer, nullable=False, default=0)

    # Contestants — NULL until the feeding matches resolve ("TBD").
    side_a_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    side_b_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)

    # Logistics (organizer-set, per-match or via CSV bulk-load).
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    match_link = Column(String, nullable=True)

    # pending (awaiting opponents/schedule) | scheduled | completed
    status = Column(String, nullable=False, default="pending")

    winner_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    score_a = Column(Float, nullable=True)
    score_b = Column(Float, nullable=True)

    # Where the winner advances: the next match + which side ("a" | "b"). NULL for
    # the final.
    next_match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id", ondelete="SET NULL"), nullable=True)
    next_slot = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    event = relationship("Event", backref="matches")
