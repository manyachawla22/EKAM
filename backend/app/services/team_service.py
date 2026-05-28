from sqlalchemy.future import select

from app.models.participant import Team, TeamMember


class TeamService:

    @staticmethod
    async def create_team(
        db,
        team_data
    ):

        team = Team(**team_data.model_dump())

        db.add(team)

        await db.commit()
        await db.refresh(team)

        return team


    @staticmethod
    async def add_team_member(
        db,
        member_data
    ):

        member = TeamMember(
            **member_data.model_dump()
        )

        db.add(member)

        await db.commit()
        await db.refresh(member)

        return member


    @staticmethod
    async def list_teams(
        db,
        event_id
    ):

        result = await db.execute(
            select(Team).where(
                Team.event_id == event_id
            )
        )

        return result.scalars().all()