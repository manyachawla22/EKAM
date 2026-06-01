import enum
from typing import Literal

ActorType = Literal[
    "organizer",
    "admin",
    "participant",
    "judge"
]

class ResourceType(str, enum.Enum):
    EVENT = "event"
    ROUND = "round"
    TEAM = "team"
    PARTICIPANT = "participant"
    JUDGE = "judge"
    SUBMISSION = "submission"
    EVALUATION = "evaluation"
    REPORT = "report"
    APPROVAL = "approval"

class Permission(str, enum.Enum):
    READ = "read"
    WRITE = "write"
    MANAGE = "manage"
    EVALUATE = "evaluate"

# Basic RBAC definitions
ROLE_PERMISSIONS = {
    "admin": [Permission.MANAGE],
    "organizer": [Permission.MANAGE],
    "judge": [Permission.READ, Permission.EVALUATE],
    "participant": [Permission.READ, Permission.WRITE]
}
