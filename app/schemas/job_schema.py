from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum
import uuid


class StepStatus(Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class StepType(Enum):
    DATAFLOW_TYPE_gateway = "gateway"
    DATAFLOW_TYPE_processing = "data_processing"
    DATAFLOW_TYPE_processing_llm = "data_processing_llm"
    DATAFLOW_TYPE_DATASINK = "data_sink"


class JobBase(BaseModel):
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    user_id: Optional[uuid.UUID]
    updated_at: datetime = datetime.now(timezone.utc)

    @field_validator('updated_at', mode='before', check_fields=False)
    def set_updated_at(cls, v):
        return v or datetime.now(timezone.utc)


class JobResponse(JobBase):
    id: uuid.UUID


class ResourceBase(BaseModel):
    job_id: uuid.UUID
    resource_type: str
    resource_data: dict
    created_at:Optional[datetime] = datetime.now(timezone.utc)
    updated_at: Optional[datetime] = datetime.now(timezone.utc)

    class Config:
        orm_mode = True


class ResourceCreate(BaseModel):
    user_id: str
    resource_type: str
    resource_data: dict


class ResourceUpdate(BaseModel):
    job_id: Optional[uuid.UUID]
    resource_type: Optional[str]
    resource_data: Optional[dict]

    @field_validator('updated_at', mode='before', check_fields=False)
    def set_updated_at(cls, v):
        return v or datetime.now(timezone.utc)


class ResourceResponse(ResourceBase):
    id: uuid.UUID


class DocumentBase(BaseModel):
    job_id: uuid.UUID
    collection_name: str
    vector_db_id: str
    created_at: Optional[datetime] = datetime.now(timezone.utc)
    updated_at: Optional[datetime] = datetime.now(timezone.utc)
    class Config:
        orm_mode = True


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    job_id: Optional[uuid.UUID]
    collection_name: Optional[str]
    vector_db_id: Optional[str]

    @field_validator('updated_at', mode='before', check_fields=False)
    def set_updated_at(cls, v):
        return v or datetime.now(timezone.utc)


class DocumentResponse(DocumentBase):
    id: uuid.UUID


class StepBase(BaseModel):
    job_id: uuid.UUID
    status: StepStatus
    step_type: StepType

    class Config:
        orm_mode = True


class StepCreate(StepBase):
    pass


class StepUpdate(BaseModel):
    job_id: Optional[uuid.UUID] = None
    status: Optional[StepStatus] = None
    step_type: Optional[StepType] = None
    updated_at: Optional[datetime] = None

    @field_validator('updated_at', mode='before', check_fields=False)
    def set_updated_at(cls, v):
        return v or datetime.now(timezone.utc)


class StepResponse(StepBase):
    id: uuid.UUID
