from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


async def create_report_service(
    db: AsyncSession,
    report_data,
    current_user=None
):
    # Placeholder
    pass

async def list_reports_service(
    db: AsyncSession,
    event_id: str
):
    # Placeholder
    pass
