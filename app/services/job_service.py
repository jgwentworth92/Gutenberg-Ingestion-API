# services/job_service.py

from datetime import datetime, timezone
from typing import Dict, List
from uuid import UUID

from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from app.models.job_resource_document_models import Job
from app.schemas.job_schema import JobCreate, JobUpdate
from app.services.base_service import BaseService


class JobService(BaseService):

    @classmethod
    async def create_job(cls, session: AsyncSession, job_data: Dict[str, str]) -> Job:
        try:
            validated_data = JobCreate(**job_data).model_dump()
            new_job = Job(**validated_data)
            session.add(new_job)
            await session.commit()
            await session.refresh(new_job)
            return new_job
        except ValidationError as e:
            raise e

    @classmethod
    async def update_job(cls, session: AsyncSession, job_id: UUID, update_data: Dict[str, str]) -> Job:
        try:
            validated_data = JobUpdate(**update_data).model_dump(exclude_unset=True)
            query = (
                update(Job)
                .where(Job.id == job_id)
                .values(**validated_data)
                .execution_options(synchronize_session="fetch")
            )
            await cls._execute_query(session, query)
            updated_job = await cls.get_job_by_id(session, job_id)
            return updated_job
        except Exception as e:
            raise e

    @classmethod
    async def get_job_by_id(cls, session: AsyncSession, job_id: UUID) -> Job:
        query = select(Job).filter_by(id=job_id)
        result = await cls._execute_query(session, query)
        return result.scalars().first()

    @classmethod
    async def get_all_jobs_by_user_id(cls, session: AsyncSession, user_id: UUID) -> List[Job]:
        query = select(Job).filter_by(user_id=user_id)
        result = await cls._execute_query(session, query)
        return list(result.scalars())

    @classmethod
    async def delete_job(cls, session: AsyncSession, job_id: UUID) -> None:
        job = await cls.get_job_by_id(session, job_id)
        if job:
            await session.delete(job)
            await session.commit()
