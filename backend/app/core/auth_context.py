from dataclasses import dataclass, field
from typing import Union, List
from uuid import UUID

from app.models.user import User
from app.models.participant import Participant
from app.models.judge import Judge

from app.core.roles import ActorType, Permission, ROLE_PERMISSIONS


@dataclass
class AuthContext:
    actor_id: str
    actor_type: ActorType
    entity: Union[User, Participant, Judge]
    
    event_id: str | None = None
    session_id: str | None = None
    
    permissions: List[Permission] = field(default_factory=list)
    is_event_scoped: bool = False

    def __post_init__(self):
        if not self.permissions:
            # Assign default permissions based on actor_type
            self.permissions = ROLE_PERMISSIONS.get(self.actor_type, [])
            
        if self.actor_type in ["participant", "judge"] or self.event_id:
            self.is_event_scoped = True

    def can_access_event(self, event_id: str | UUID) -> bool:
        if self.actor_type in ["admin", "organizer"]:
            return True
        # Firebase-authenticated participants/judges are cross-event users —
        # their JWT carries no event_id. Allow the access gate to pass; the
        # service layer is responsible for filtering returned rows by
        # event_id when that matters (e.g. listing participants of an event).
        # Only OTP/magic-link sessions carry a non-null event_id, and those
        # must match the requested event.
        if not self.event_id:
            return True
        return str(self.event_id) == str(event_id)

    def can_manage_entity(self, entity_id: str | UUID) -> bool:
        if self.actor_type in ["admin", "organizer"]:
            return True
        return str(self.actor_id) == str(entity_id)