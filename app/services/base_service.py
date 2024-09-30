# services/base_service.py

from sqlalchemy.ext.asyncio import AsyncSession

class BaseService:
    @classmethod
    async def _execute_query(cls, session: AsyncSession, query):
        return await session.execute(query)
