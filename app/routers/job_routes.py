# app/routes.py

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, AsyncGenerator
from uuid import UUID


from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_db,
    get_job_service,
    get_resource_service,
    get_step_service,
    get_document_service,
    get_global_listener_dependency
)
from app.schemas.job_schema import (
    JobResponse,
    ResourceResponse,
    ResourceCreate,
    DocumentResponse,
    DocumentCreate,
    StepResponse,
    StepUpdate,
    CollectionsInfoResponse,
    StepType
)
from app.services.GlobalListener_service import IGlobalListener
from app.services.document_service import DocumentService
from app.services.job_service import JobService
from app.services.resource_service import ResourceService
from app.services.step_service import StepService

# Initialize logger
logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------
# Job Routes
# ---------------------

@router.get("/jobs/{job_id}", response_model=JobResponse, tags=["Job Management"])
async def get_job(
        job_id: UUID,
        db: AsyncSession = Depends(get_db),
        job_service: JobService = Depends(get_job_service)
):
    job = await job_service.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobResponse.model_construct(**job.__dict__)


@router.get("/jobs/user/{user_id}", response_model=List[JobResponse], tags=["Job Management"])
async def get_all_jobs_by_user_id(
        user_id: UUID,
        db: AsyncSession = Depends(get_db),
        job_service: JobService = Depends(get_job_service)
):
    jobs = await job_service.get_all_jobs_by_user_id(db, user_id)
    return [JobResponse.model_construct(**job.__dict__) for job in jobs]


# ---------------------
# Resource Routes
# ---------------------


@router.get("/resources/{resource_id}", response_model=ResourceResponse, tags=["Resource Management"])
async def get_resource(
        resource_id: UUID,
        db: AsyncSession = Depends(get_db),
        resource_service: ResourceService = Depends(get_resource_service)
):
    resource = await resource_service.get_resource_by_id(db, resource_id)
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return ResourceResponse.model_construct(**resource.__dict__)



@router.get("/resources/user/{user_id}", response_model=List[ResourceResponse], tags=["Resource Management"])
async def get_all_resources_by_user_id(
        user_id: UUID,
        db: AsyncSession = Depends(get_db),
        resource_service: ResourceService = Depends(get_resource_service)
):
    resources = await resource_service.get_all_resources_by_user_id(db, user_id)
    return [ResourceResponse.model_construct(**resource.__dict__) for resource in resources]


# ---------------------
# Document Routes
# ---------------------

@router.post(
    "/documents/batch/",
    response_model=List[DocumentResponse],
    status_code=status.HTTP_201_CREATED,
    tags=["Document Management"]
)
async def create_multiple_documents(
        documents: List[DocumentCreate],
        db: AsyncSession = Depends(get_db),
        document_service: DocumentService = Depends(get_document_service),
        global_listener: IGlobalListener = Depends(get_global_listener_dependency)
):
    created_documents = []
    for document in documents:
        try:
            created_document = await document_service.create_document(db, document.dict())
            created_documents.append(DocumentResponse.model_construct(**created_document.__dict__))

            # Publish each document creation event
            update_data = {
                "document_id": str(created_document.id),
                "status": "CREATED",
                "created_at": str(created_document.created_at)
            }
            await global_listener.publish_update(created_document.job_id, update_data)
        except ValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.errors())
    return created_documents


@router.get("/documents/{document_id}", response_model=DocumentResponse, tags=["Document Management"])
async def get_document(
        document_id: UUID,
        db: AsyncSession = Depends(get_db),
        document_service: DocumentService = Depends(get_document_service)
):
    document = await document_service.get_document_by_id(db, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentResponse.model_construct(**document.__dict__)



@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Document Management"])
async def delete_document(
        document_id: UUID,
        db: AsyncSession = Depends(get_db),
        document_service: DocumentService = Depends(get_document_service),
        global_listener: IGlobalListener = Depends(get_global_listener_dependency)
):
    try:
        document = await document_service.get_document_by_id(db, document_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        await document_service.delete_document(db, document_id)

        # Publish document deletion event
        update_data = {
            "document_id": str(document_id),
            "status": "DELETED",
            "deleted_at": str(datetime.now(timezone.utc))
        }
        await global_listener.publish_update(document.job_id, update_data)

    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/documents/job/{job_id}", response_model=List[DocumentResponse], tags=["Document Management"])
async def get_all_documents_by_job_id(
        job_id: UUID,
        db: AsyncSession = Depends(get_db),
        document_service: DocumentService = Depends(get_document_service)
):
    documents = await document_service.get_all_documents_by_job_id(db, job_id)
    return [DocumentResponse.model_construct(**document.__dict__) for document in documents]


@router.get("/documents/user/{user_id}", response_model=List[DocumentResponse], tags=["Document Management"])
async def get_all_documents_by_user_id(
        user_id: UUID,
        db: AsyncSession = Depends(get_db),
        document_service: DocumentService = Depends(get_document_service)
):
    documents = await document_service.get_all_documents_by_user_id(db, user_id)
    return [DocumentResponse.model_construct(**document.__dict__) for document in documents]


@router.get("/collections/user/{user_id}", response_model=CollectionsInfoResponse, tags=["Document Management"])
async def get_collections_info(
        user_id: UUID,
        db: AsyncSession = Depends(get_db),
        document_service: DocumentService = Depends(get_document_service)
):
    """
    Retrieve all collections' vector_db_id and document_type grouped by collections for a specific user.
    """
    collections_info = await document_service.get_collections_info(db, user_id)
    return collections_info


# ---------------------
# Step Routes
# ---------------------



@router.get("/steps/{step_id}", response_model=StepResponse, tags=["Step Management"])
async def get_step(
        step_id: UUID,
        db: AsyncSession = Depends(get_db),
        step_service: StepService = Depends(get_step_service)
):
    step = await step_service.get_step_by_id(db, step_id)
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step not found")
    return StepResponse.model_construct(**step.__dict__)






@router.put(
    "/jobs/{job_id}/steps/{step_type}",
    response_model=StepResponse,
    tags=["Step Management"]
)
async def update_step_by_job_id_and_type(
        job_id: UUID,
        step_type: StepType,
        step_update: StepUpdate,
        db: AsyncSession = Depends(get_db),
        step_service: StepService = Depends(get_step_service),
        global_listener: IGlobalListener = Depends(get_global_listener_dependency)
):
    logger.info(f"Received request to update step. Job ID: {job_id}, Step Type: {step_type}")
    try:
        step = await step_service.get_step_by_job_id_and_type(db, job_id, step_type)
        if not step:
            logger.warning(f"Step not found. Job ID: {job_id}, Step Type: {step_type}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step not found")

        logger.info(f"Updating step. Job ID: {job_id}, Step ID: {step.id}")
        updated_step = await step_service.update_step(db, step.id, step_update.dict(exclude_unset=True))
        logger.info(f"Step updated successfully. Job ID: {job_id}, Step ID: {updated_step.id}")

        update_data = {
            "step_id": str(updated_step.id),
            "step_type": str(updated_step.step_type.value),
            "status": str(updated_step.status.value),
            "updated_at": str(updated_step.updated_at)
        }
        logger.info(f"Publishing update to global listener. Job ID: {job_id}, Update: {update_data}")
        await global_listener.publish_update(job_id, update_data)

        logger.info(f"Returning updated step response. Job ID: {job_id}, Step ID: {updated_step.id}")
        return StepResponse.model_construct(**updated_step.__dict__)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error updating step. Job ID: {job_id}, Step Type: {step_type}. Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/steps/job/{job_id}", response_model=List[StepResponse], tags=["Step Management"])
async def get_all_steps_by_job_id(
        job_id: UUID,
        db: AsyncSession = Depends(get_db),
        step_service: StepService = Depends(get_step_service)
):
    steps = await step_service.get_all_steps_by_job_id(db, job_id)
    return [StepResponse.model_construct(**step.__dict__) for step in steps]


# ---------------------
# Streaming Endpoint
# ---------------------

@router.post(
    "/resources/stream/",
    status_code=status.HTTP_201_CREATED,
    tags=["Resource Management"]
)
async def create_resource_and_stream(
        resource: ResourceCreate,
        db: AsyncSession = Depends(get_db),
        resource_service: ResourceService = Depends(get_resource_service),
        step_service: StepService = Depends(get_step_service),
        global_listener: IGlobalListener = Depends(get_global_listener_dependency)
):
    logger.info(f"Received request to create resource and stream updates")

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Create the resource using ResourceService
            created_resource = await resource_service.create_resource(db, resource.dict())
            job_id = created_resource.job_id

            # Send the initial resource creation response
            initial_response = ResourceResponse.model_construct(**created_resource.__dict__)
            yield f"data: {json.dumps({'type': 'resource_created', 'data': initial_response.model_dump_json()})}\n\n"

            # Get the list of step IDs associated with the job
            steps = await step_service.get_all_steps_by_job_id(db, job_id)
            step_ids = set(str(step.id) for step in steps)
            total_steps = len(step_ids)

            # Track the completion status of each step
            completed_steps = set()

            # Subscribe to updates
            update_queue = await global_listener.subscribe(job_id)

            start_time = datetime.now(timezone.utc)
            timeout = timedelta(minutes=30)  # Adjust TIMEOUT_MINUTES as needed

            try:
                while True:
                    if datetime.now(timezone.utc) - start_time > timeout:
                        logger.info(f"Timeout reached for Job ID {job_id}. Ending stream.")
                        yield f"data: {json.dumps({'type': 'timeout', 'message': 'Job processing timed out'})}\n\n"
                        break

                    try:
                        # Wait for an update or timeout after 30 seconds
                        update = await asyncio.wait_for(update_queue.get(), timeout=30)
                        yield f"data: {json.dumps({'type': 'job_update', 'data': update})}\n\n"

                        step_id = update.get('step_id')
                        step_status = update.get('status')
                        if step_status == 'FAILED':
                            yield f"data: {json.dumps({'type': 'job_FAILED', 'message': f'JOB FAILED for {update.get('step_type')}'})}\n\n"
                            break

                        logger.info(f"Received update for step ID {step_id}: {update}")

                        if step_id in step_ids and step_status == 'COMPLETE':
                            completed_steps.add(step_id)
                            logger.info(
                                f"Step {step_id} marked as completed. Progress: {len(completed_steps)}/{total_steps}"
                            )

                        # If all steps are completed, end the stream
                        if completed_steps == step_ids:
                            logger.info(f"All steps for Job ID {job_id} are completed. Ending stream.")
                            yield f"data: {json.dumps({'type': 'job_completed', 'message': 'All steps completed'})}\n\n"
                            break

                    except asyncio.TimeoutError:
                        # No update received, continue the loop
                        continue

            except Exception as e:
                logger.error(f"Error in event generator: {str(e)}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

            finally:
                logger.info(f"Unsubscribing from updates for Job ID: {job_id}")
                await global_listener.unsubscribe(job_id, update_queue)

        except ValidationError as e:
            logger.error(f"Validation error during resource creation: {e.errors()}")
            yield f"data: {json.dumps({'type': 'error', 'message': e.errors()})}\n\n"
        except Exception as e:
            logger.error(f"Unexpected error during resource creation and streaming: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': 'Internal Server Error'})}\n\n"

    logger.info(f"Returning StreamingResponse for resource creation and updates")
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )