from app.services.cpsat_team_service import CPsatTeamService
from app.services.cpsat_judge_service import CPsatJudgeService

from app.services.team_service import TeamService
from app.services.judge_service import JudgeService

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import TeamMember
from app.models.judge import JudgeAssignment


class AssignmentService:

    # =========================================================
    # TEAM GENERATION
    # =========================================================

    @staticmethod
    async def auto_generate_teams(
        db: AsyncSession,
        participants,
        constraints
    ):

        generated_teams = (
            await CPsatTeamService.generate_teams(
                participants,
                constraints
            )
        )

        return generated_teams

    @staticmethod
    async def save_generated_teams(
        db: AsyncSession,
        teams_data
    ):

        created_teams = []

        for team_data in teams_data:

            team = await TeamService.create_team(
                db=db,
                team_data=team_data
            )

            created_teams.append(team)

        return created_teams

    # =========================================================
    # JUDGE ASSIGNMENT
    # =========================================================

    @staticmethod
    async def auto_generate_judge_assignments(
        db: AsyncSession,
        judges,
        teams,
        constraints
    ):

        assignments = (
            await CPsatJudgeService.generate_assignments(
                judges=judges,
                teams=teams,
                constraints=constraints
            )
        )

        return assignments

    @staticmethod
    async def save_judge_assignments(
        db: AsyncSession,
        assignments_data
    ):

        created_assignments = []

        for assignment_data in assignments_data:

            assignment = await JudgeService.create_assignment(
                db=db,
                assignment_data=assignment_data
            )

            created_assignments.append(assignment)

        return created_assignments

    # =========================================================
    # MANUAL TEAM ASSIGNMENT
    # =========================================================

    @staticmethod
    async def assign_team_member(
        db: AsyncSession,
        member_data
    ):

        member = TeamMember(
            **member_data.model_dump()
        )

        db.add(member)

        await db.commit()
        await db.refresh(member)

        return member

    # =========================================================
    # MANUAL JUDGE ASSIGNMENT
    # =========================================================

    @staticmethod
    async def assign_single_judge(
        db: AsyncSession,
        assignment_data
    ):

        assignment = JudgeAssignment(
            **assignment_data.model_dump()
        )

        db.add(assignment)

        await db.commit()
        await db.refresh(assignment)

        return assignment