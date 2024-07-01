from datetime import datetime, timezone
from typing import Dict, List, Any, Sequence
from pydantic import ValidationError
from sqlalchemy import update, select, Row, RowMapping, func
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.models.job_resource_document_models import Job, Resource, Step, Document
from app.schemas.job_schema import JobCreate, JobUpdate, ResourceCreate, ResourceUpdate, StepCreate, StepUpdate, \
    DocumentUpdate, DocumentCreate, StepType, StepStatus, CollectionsInfoResponse, CollectionInfo
from enum import Enum







class JobService:

    @classmethod
    async def _execute_query(cls, session: AsyncSession, query):
        return await session.execute(query)

    # Job CRUD operations
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
            query = update(Job).where(Job.id == job_id).values(**validated_data).execution_options(
                synchronize_session="fetch")
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
        return [job for job in result.scalars()]

    @classmethod
    async def _delete_job(cls, session: AsyncSession, job_id: UUID) -> None:
        job = await cls.get_job_by_id(session, job_id)
        await session.delete(job)
        await session.commit()

    # Resource CRUD operations
    @classmethod
    async def create_resource(cls, session: AsyncSession, resource_data: Dict[str, str]) -> Resource:
        try:
            validated_data = ResourceCreate(**resource_data).model_dump()
            job_data = {
                "user_id": validated_data.pop("user_id"),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            new_job = await cls.create_job(session, job_data)
            validated_data['job_id'] = new_job.id
            new_resource = Resource(**validated_data)
            session.add(new_resource)
            await session.commit()
            await session.refresh(new_resource)

            # Automatically create steps for the new job
            for step_type in StepType:
                step_data = {
                    "job_id": new_job.id,
                    "step_type": step_type.value,
                    "status": 'NOT_STARTED',
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
                await cls.create_step(session, step_data)

            return new_resource
        except ValidationError as e:
            raise e

    @classmethod
    async def update_resource(cls, session: AsyncSession, resource_id: UUID, update_data: Dict[str, str]) -> Resource:
        try:
            validated_data = ResourceUpdate(**update_data).model_dump(exclude_unset=True)
            query = update(Resource).where(Resource.id == resource_id).values(**validated_data).execution_options(
                synchronize_session="fetch")
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
        jobs = await cls.get_all_jobs_by_user_id(session, user_id)
        job_ids = [job.id for job in jobs]
        query = select(Resource).filter(Resource.job_id.in_(job_ids))
        result = await cls._execute_query(session, query)
        return [resource for resource in result.scalars()]

    @classmethod
    async def delete_resource(cls, session: AsyncSession, resource_id: UUID) -> None:
        resource = await cls.get_resource_by_id(session, resource_id)
        if resource:
            job_id = resource.job_id
            # Delete associated steps
            query = select(Step).filter_by(job_id=job_id)
            steps = await cls._execute_query(session, query)
            for step in steps.scalars():
                await cls._delete_step(session, step.id)

            # Delete the job
            await cls._delete_job(session, job_id)

            # Delete the resource
            await session.delete(resource)
            await session.commit()

    # Step CRUD operations
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
    async def update_step(cls, session: AsyncSession, step_id: UUID, update_data: Dict[str, str]) -> Step:
        try:
            validated_data = StepUpdate(**update_data).model_dump(exclude_unset=True)
            query = update(Step).where(Step.id == step_id).values(**validated_data).execution_options(
                synchronize_session="fetch")
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
        return [step for step in result.scalars()]

    @classmethod
    async def _delete_step(cls, session: AsyncSession, step_id: UUID) -> None:
        step = await cls.get_step_by_id(session, step_id)
        await session.delete(step)
        await session.commit()
        await session.commit()

    @classmethod
    async def create_document(cls, session: AsyncSession, document_data: Dict[str, str]) -> Document:
        try:
            validated_data = DocumentCreate(**document_data).model_dump()
            new_document = Document(**validated_data)
            session.add(new_document)
            await session.commit()
            await session.refresh(new_document)
            return new_document
        except ValidationError as e:
            raise e

    @classmethod
    async def update_document(cls, session: AsyncSession, document_id: UUID, update_data: Dict[str, str]) -> Document:
        try:
            validated_data = DocumentUpdate(**update_data).model_dump(exclude_unset=True)
            query = update(Document).where(Document.id == document_id).values(**validated_data).execution_options(
                synchronize_session="fetch")
            await cls._execute_query(session, query)
            updated_document = await cls.get_document_by_id(session, document_id)
            return updated_document
        except Exception as e:
            raise e

    @classmethod
    async def get_document_by_id(cls, session: AsyncSession, document_id: UUID) -> Document:
        query = select(Document).filter_by(id=document_id)
        result = await cls._execute_query(session, query)
        return result.scalars().first()

    @classmethod
    async def delete_document(cls, session: AsyncSession, document_id: UUID) -> None:
        document = await cls.get_document_by_id(session, document_id)
        await session.delete(document)
        await session.commit()

    @classmethod
    async def get_all_documents_by_user_id(cls, session: AsyncSession, user_id: UUID) -> List[Document]:
        jobs = await cls.get_all_jobs_by_user_id(session, user_id)
        job_ids = [job.id for job in jobs]
        query = select(Document).filter(Document.job_id.in_(job_ids))
        result = await cls._execute_query(session, query)
        return [document for document in result.scalars()]

    @classmethod
    async def get_all_documents_by_job_id(cls, session: AsyncSession, job_id: UUID) -> List[Document]:
        query = select(Document).filter_by(job_id=job_id)
        result = await cls._execute_query(session, query)
        return [document for document in result.scalars()]

    @classmethod
    async def get_collections_info(cls, session: AsyncSession, user_id: UUID) -> CollectionsInfoResponse:
        query = (
            select(
                Document.collection_name,
                func.array_agg(Document.vector_db_id).label('vector_db_ids'),
                func.array_agg(Document.document_type).label('document_types')
            )
            .join(Job, Document.job_id == Job.id)
            .filter(Job.user_id == user_id)
            .group_by(Document.collection_name)
        )
        result = await cls._execute_query(session, query)
        collections = [
            CollectionInfo(
                collection_name=row.collection_name,
                vector_db_ids=row.vector_db_ids,
                document_types=row.document_types
            )
            for row in result
        ]
        return CollectionsInfoResponse(collections=collections)