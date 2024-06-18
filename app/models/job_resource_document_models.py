# job_resource_document_models.py

from sqlalchemy import Column, ForeignKey, String, Integer, DateTime, JSON, Enum as SQLAlchemyEnum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime, timezone
from app.database import Base
from enum import Enum

from app.schemas.job_schema import StepType, StepStatus


# Add more step types as needed


class Job(Base):
    """
    Represents a job within the application, corresponding to the 'jobs' table in the database.
    """
    __tablename__ = "jobs"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="jobs")
    resources = relationship("Resource", back_populates="job", lazy='dynamic', cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="job", lazy='dynamic', cascade="all, delete-orphan")
    steps = relationship("Step", back_populates="job", lazy='dynamic', cascade="all, delete-orphan")


class Resource(Base):
    """
    Represents a resource within the application, corresponding to the 'resources' table in the database.
    """
    __tablename__ = "resources"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('jobs.id'), nullable=False)
    resource_type: Mapped[str] = Column(String(50), nullable=False)
    resource_data: Mapped[dict] = Column(JSON, nullable=False)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    job = relationship("Job", back_populates="resources")


class Document(Base):
    """
    Represents a document within the application, corresponding to the 'documents' table in the database.
    """
    __tablename__ = "documents"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('jobs.id'), nullable=False)
    collection_name: Mapped[str] = Column(String(255), nullable=False)
    vector_db_id: Mapped[str] = Column(String(255), nullable=False)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    job = relationship("Job", back_populates="documents")


class Step(Base):
    """
    Represents a step within a job, corresponding to the 'steps' table in the database.
    """
    __tablename__ = "steps"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('jobs.id'), nullable=False)
    status: Mapped[StepStatus] = Column(SQLAlchemyEnum(StepStatus), nullable=False, default=StepStatus.NOT_STARTED)
    step_type: Mapped[StepType] = Column(SQLAlchemyEnum(StepType), nullable=False)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # add error info to table
    job = relationship("Job", back_populates="steps")

