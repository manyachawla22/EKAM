import enum

class EmailType(str, enum.Enum):
    invitation = "invitation"
    team_assignment = "team_assignment"
    stage_update = "stage_update"
    magic_link = "magic_link"
    result = "result"
    progression = "progression"
    certificate = "certificate"
