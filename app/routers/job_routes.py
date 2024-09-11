import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, status, Body, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.dependencies import get_db, require_role
from app.schemas.job_schema import JobResponse, JobCreate, JobUpdate, ResourceResponse, ResourceCreate, ResourceUpdate, \
    DocumentResponse, DocumentCreate, DocumentUpdate, StepCreate, StepResponse, StepUpdate, CollectionsInfoResponse, \
    StepType, StepBase, StepStatus
from app.services.job_service import JobService
active_connections: Dict[UUID, WebSocket] = {}
# Set the timeout duration
router = APIRouter()
# Set the timeout duration
TIMEOUT_MINUTES = 5  # Set the timeout duration

@router.websocket("/ws/resource/{job_id}")
async def websocket_resource_status(websocket: WebSocket, job_id: UUID, db: AsyncSession = Depends(get_db)):
    await websocket.accept()
    start_time = datetime.now()

    try:
        while True:
            job = await JobService.get_job_by_id(db, job_id)
            if not job:
                await websocket.send_json({"error": "Job not found"})
                break

            steps = await JobService.get_all_steps_by_job_id(db, job_id)

            status_update = {
                "job_id": str(job.id),
                "status": job.status,
                "steps": [
                    {
                        "step_type": step.step_type,
                        "status": step.status,
                        "total_documents": step.total_documents,
                        "processed_documents": step.processed_documents,
                        "error_info": step.error_info
                    } for step in steps
                ]
            }

            await websocket.send_json(status_update)

            # Check if all steps are completed
            all_completed = all(step.status == StepStatus.COMPLETE for step in steps)

            # Check if any step has failed
            any_failed = any(step.status == StepStatus.FAILED for step in steps)

            # Check for timeout
            time_elapsed = datetime.now() - start_time
            is_timeout = time_elapsed > timedelta(minutes=TIMEOUT_MINUTES)

            if all_completed:
                await websocket.send_json({"message": "All steps completed"})
                break
            elif any_failed:
                await websocket.send_json({"message": "Job failed", "failed_steps": [step.step_type for step in steps if
                                                                                     step.status == StepStatus.FAILED]})
                break
            elif is_timeout:
                await websocket.send_json({"message": "Job timed out"})
                break

            # Wait for 5 seconds before the next update
            await asyncio.sleep(5)

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for job {job_id}")
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        print(f"Closing WebSocket connection for job {job_id}")
        await websocket.close()

@router.get("/jobs/{job_id}", response_model=JobResponse, tags=["Job Management"])
async def get_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    job = await JobService.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobResponse.model_construct(**job.__dict__)


# Resource Routes
@router.post("/resources/", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED,
             tags=["Resource Management"])
async def create_resource(resource: ResourceCreate, db: AsyncSession = Depends(get_db)):
    created_resource = await JobService.create_resource(db, resource.dict())
    return ResourceResponse.model_construct(**created_resource.__dict__)


@router.get("/resources/{resource_id}", response_model=ResourceResponse, tags=["Resource Management"])
async def get_resource(resource_id: UUID, db: AsyncSession = Depends(get_db)):
    resource = await JobService.get_resource_by_id(db, resource_id)
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return ResourceResponse.model_construct(**resource.__dict__)


@router.put("/resources/{resource_id}", response_model=ResourceResponse, tags=["Resource"])
async def update_resource(resource_id: UUID, resource_update: ResourceUpdate, db: AsyncSession = Depends(get_db)):
    updated_resource = await JobService.update_resource(db, resource_id, resource_update.dict(exclude_unset=True))
    return ResourceResponse.model_construct(**updated_resource.__dict__)


@router.delete("/resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Resource"])
async def delete_resource(resource_id: UUID, db: AsyncSession = Depends(get_db)):
    await JobService.delete_resource(db, resource_id)


# Document Routes
@router.post("/documents/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED,
             tags=["Document Management"])
async def create_document(document: DocumentCreate, db: AsyncSession = Depends(get_db)):
    created_document = await JobService.create_document(db, document.dict())
    return DocumentResponse.model_construct(**created_document.__dict__)


@router.post("/documents/batch/", response_model=List[DocumentResponse], status_code=status.HTTP_201_CREATED,
             tags=["Document Management"])
async def create_multiple_documents(documents: List[DocumentCreate], db: AsyncSession = Depends(get_db)):
    created_documents = []
    for document in documents:
        created_document = await JobService.create_document(db, document.dict())
        created_documents.append(DocumentResponse.model_construct(**created_document.__dict__))
    return created_documents


@router.get("/documents/{document_id}", response_model=DocumentResponse, tags=["Document Manage"])
async def get_document(document_id: UUID, db: AsyncSession = Depends(get_db)):
    document = await JobService.get_document_by_id(db, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentResponse.model_construct(**document.__dict__)


@router.put("/documents/{document_id}", response_model=DocumentResponse, tags=["Document Management"])
async def update_document(document_id: UUID, document_update: DocumentUpdate, db: AsyncSession = Depends(get_db)):
    updated_document = await JobService.update_document(db, document_id, document_update.dict(exclude_unset=True))
    return DocumentResponse.model_construct(**updated_document.__dict__)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Document Management"])
async def delete_document(document_id: UUID, db: AsyncSession = Depends(get_db)):
    await JobService.delete_document(db, document_id)


# Step Routes
@router.post("/steps/", response_model=StepResponse, status_code=status.HTTP_201_CREATED, tags=["Step Management"])
async def create_step(step: StepCreate, db: AsyncSession = Depends(get_db)):
    created_step = await JobService.create_step(db, step.dict())
    return StepResponse.model_construct(**created_step.__dict__)


@router.get("/steps/{step_id}", response_model=StepResponse, tags=["Step Management"])
async def get_step(step_id: UUID, db: AsyncSession = Depends(get_db)):
    step = await JobService.get_step_by_id(db, step_id)
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step not found")
    return StepResponse.model_construct(**step.__dict__)


@router.put("/steps/{step_id}", response_model=StepResponse, tags=["Step Management"])
async def update_step(step_id: UUID, step_update: StepUpdate, db: AsyncSession = Depends(get_db)):
    updated_step = await JobService.update_step(db, step_id, step_update.dict(exclude_unset=True))
    return StepResponse.model_construct(**updated_step.__dict__)


@router.patch("/steps/{step_id}", response_model=StepResponse, tags=["Step Management"])
async def patch_step(step_id: UUID, step_update: StepUpdate, db: AsyncSession = Depends(get_db)):
    updated_step = await JobService.update_step(db, step_id, step_update.dict(exclude_unset=True))
    return StepResponse.model_construct(**updated_step.__dict__)


@router.put("/jobs/{job_id}/steps/{step_type}", response_model=StepResponse, tags=["Step Management"])
async def update_step_by_job_id_and_type(
        job_id: UUID, step_type: StepType, step_update: StepUpdate, db: AsyncSession = Depends(get_db)
):
    try:
        step = await JobService.get_step_by_job_id_and_type(db, job_id, step_type)
        if not step:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step not found")
        updated_step = await JobService.update_step(db, step.id, step_update.dict(exclude_unset=True))
        return StepResponse.model_construct(**updated_step.__dict__)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/jobs/user/{user_id}", response_model=List[JobResponse], tags=["Job Management"])
async def get_all_jobs_by_user_id(user_id: UUID, db: AsyncSession = Depends(get_db)):
    jobs = await JobService.get_all_jobs_by_user_id(db, user_id)
    return [JobResponse.model_construct(**job.__dict__) for job in jobs]


# Resource Routes
@router.get("/resources/user/{user_id}", response_model=List[ResourceResponse], tags=["Resource Management"])
async def get_all_resources_by_user_id(user_id: UUID, db: AsyncSession = Depends(get_db)):
    resources = await JobService.get_all_resources_by_user_id(db, user_id)
    return [ResourceResponse.model_construct(**resource.__dict__) for resource in resources]


# Step Routes
@router.get("/steps/job/{job_id}", response_model=List[StepResponse], tags=["Step Management"])
async def get_all_steps_by_job_id(job_id: UUID, db: AsyncSession = Depends(get_db)):
    steps = await JobService.get_all_steps_by_job_id(db, job_id)
    return [StepResponse.model_construct(**step.__dict__) for step in steps]


# Document Routes
@router.get("/documents/job/{job_id}", response_model=List[DocumentResponse], tags=["Document Management"])
async def get_all_documents_by_job_id(job_id: UUID, db: AsyncSession = Depends(get_db)):
    documents = await JobService.get_all_documents_by_job_id(db, job_id)
    return [DocumentResponse.model_construct(**document.__dict__) for document in documents]


@router.get("/documents/user/{user_id}", response_model=List[DocumentResponse], tags=["Document Management"])
async def get_all_documents_by_user_id(user_id: UUID, db: AsyncSession = Depends(get_db)):
    documents = await JobService.get_all_documents_by_user_id(db, user_id)
    return [DocumentResponse.model_construct(**document.__dict__) for document in documents]


@router.get("/collections/user/{user_id}", response_model=CollectionsInfoResponse, tags=["Document Management_TEST"])
async def get_collections_info(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Retrieve all collections' vector_db_id and document_type grouped by collections for a specific user.
    """
    collections_info = await JobService.get_collections_info(db, user_id)
    return collections_info

