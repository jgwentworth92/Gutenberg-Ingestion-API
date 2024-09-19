# services/step_service.py

from typing import Dict, List
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from app.models.job_resource_document_models import Step
from app.schemas.job_schema import StepCreate, StepUpdate, StepType
from app.services.base_service import BaseService


class StepService(BaseService):

    @classmethod
    async def create_step(cls, session: AsyncSession, step_data: Dict[str, str]) -> Step:
        try:
            validated_data = StepCreate(**step_data).model_dump()
            new_step = Step(**validated_data)
            session.add(new_step)
            await session.commit()
            await session.refresh(new_step)
            return new_step
        except ValidationError as e:
            raise e

    @classmethod
    async def get_step_by_job_id_and_type(cls, session: AsyncSession, job_id: UUID, step_type: StepType) -> Step:
        query = select(Step).filter_by(job_id=job_id, step_type=step_type)
        result = await cls._execute_query(session, query)
        return result.scalars().first()

    @classmethod
    async def update_step(cls, session: AsyncSession, step_id: UUID, update_data: Dict[str, str]) -> Step:
        try:
            validated_data = StepUpdate(**update_data).model_dump(exclude_unset=True)
            query = (
                update(Step)
                .where(Step.id == step_id)
                .values(**validated_data)
                .execution_options(synchronize_session="fetch")
            )
            await cls._execute_query(session, query)
            await session.commit()
            updated_step = await cls.get_step_by_id(session, step_id)
            return updated_step
        except Exception as e:
            raise e

    @classmethod
    async def get_step_by_id(cls, session: AsyncSession, step_id: UUID) -> Step:
        query = select(Step).filter_by(id=step_id)
        result = await cls._execute_query(session, query)
        return result.scalars().first()

    @classmethod
    async def get_all_steps_by_job_id(cls, session: AsyncSession, job_id: UUID) -> List[Step]:
        query = select(Step).filter_by(job_id=job_id)
        result = await cls._execute_query(session, query)
        return list(result.scalars())

    @classmethod
    async def delete_step(cls, session: AsyncSession, step_id: UUID) -> None:
        step = await cls.get_step_by_id(session, step_id)
        await session.delete(step)
        await session.commit()
