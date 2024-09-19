# services/resource_service.py

from datetime import datetime, timezone
from typing import Dict, List
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from app.models.job_resource_document_models import Resource
from app.schemas.job_schema import ResourceCreate, ResourceUpdate, StepType
from app.services.base_service import BaseService
from app.services.job_service import JobService
from app.services.step_service import StepService


class ResourceService(BaseService):

    @classmethod
    async def create_resource(cls, session: AsyncSession, resource_data: Dict[str, str]) -> Resource:
        try:
            validated_data = ResourceCreate(**resource_data).model_dump()
            job_data = {
                "user_id": validated_data.pop("user_id"),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            new_job = await JobService.create_job(session, job_data)
            validated_data["job_id"] = new_job.id
            new_resource = Resource(**validated_data)
            session.add(new_resource)
            await session.commit()
            await session.refresh(new_resource)

            # Automatically create steps for the new job
            for step_type in StepType:
                step_data = {
                    "job_id": new_job.id,
                    "step_type": step_type.value,
                    "status": "NOT_STARTED",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
                await StepService.create_step(session, step_data)

            return new_resource
        except ValidationError as e:
            raise e

    @classmethod
    async def update_resource(cls, session: AsyncSession, resource_id: UUID, update_data: Dict[str, str]) -> Resource:
        try:
            validated_data = ResourceUpdate(**update_data).model_dump(exclude_unset=True)
            query = (
                update(Resource)
                .where(Resource.id == resource_id)
                .values(**validated_data)
                .execution_options(synchronize_session="fetch")
            )
            await cls._execute_query(session, query)
            updated_resource = await cls.get_resource_by_id(session, resource_id)
            return updated_resource
        except Exception as e:
            raise e

    @classmethod
    async def get_resource_by_id(cls, session: AsyncSession, resource_id: UUID) -> Resource:
        query = select(Resource).filter_by(id=resource_id)
        result = await cls._execute_query(session, query)
        return result.scalars().first()

    @classmethod
    async def get_all_resources_by_user_id(cls, session: AsyncSession, user_id: UUID) -> List[Resource]:
        jobs = await JobService.get_all_jobs_by_user_id(session, user_id)
        job_ids = [job.id for job in jobs]
        query = select(Resource).filter(Resource.job_id.in_(job_ids))
        result = await cls._execute_query(session, query)
        return list(result.scalars())

    @classmethod
    async def delete_resource(cls, session: AsyncSession, resource_id: UUID) -> None:
        resource = await cls.get_resource_by_id(session, resource_id)
        if resource:
            job_id = resource.job_id

            # Delete associated steps
            steps = await StepService.get_all_steps_by_job_id(session, job_id)
            for step in steps:
                await StepService.delete_step(session, step.id)

            # Delete the job
            await JobService.delete_job(session, job_id)

            # Delete the resource
            await session.delete(resource)
            await session.commit()
