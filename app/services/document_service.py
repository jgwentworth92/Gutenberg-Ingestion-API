# services/document_service.py

from typing import Dict, List
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from app.models.job_resource_document_models import Document, Job
from app.schemas.job_schema import (
    DocumentCreate,
    DocumentUpdate,
    DocumentMetadata,
    CollectionInfo,
    CollectionsInfoResponse,
)
from app.services.base_service import BaseService
from app.services.job_service import JobService


class DocumentService(BaseService):

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
            query = (
                update(Document)
                .where(Document.id == document_id)
                .values(**validated_data)
                .execution_options(synchronize_session="fetch")
            )
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
        jobs = await JobService.get_all_jobs_by_user_id(session, user_id)
        job_ids = [job.id for job in jobs]
        query = select(Document).filter(Document.job_id.in_(job_ids))
        result = await cls._execute_query(session, query)
        return list(result.scalars())

    @classmethod
    async def get_all_documents_by_job_id(cls, session: AsyncSession, job_id: UUID) -> List[Document]:
        query = select(Document).filter_by(job_id=job_id)
        result = await cls._execute_query(session, query)
        return list(result.scalars())

    @classmethod
    async def get_collections_info(cls, session: AsyncSession, user_id: UUID) -> CollectionsInfoResponse:
        query = (
            select(
                Document.collection_name,
                Document.vector_db_id,
                Document.document_type,
            )
            .join(Job, Document.job_id == Job.id)
            .filter(Job.user_id == user_id)
        )
        result = await cls._execute_query(session, query)

        collections_dict = {}
        for row in result:
            if row.collection_name not in collections_dict:
                collections_dict[row.collection_name] = []
            collections_dict[row.collection_name].append(
                DocumentMetadata(vector_db_id=row.vector_db_id, doc_type=row.document_type)
            )

        collections = [
            CollectionInfo(collection_name=collection_name, collection_metadata=metadata)
            for collection_name, metadata in collections_dict.items()
        ]

        return CollectionsInfoResponse(collections=collections)
