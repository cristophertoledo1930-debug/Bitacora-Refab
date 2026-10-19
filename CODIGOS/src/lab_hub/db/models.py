import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Boolean,
    Numeric,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    CheckConstraint,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from lab_hub.db.session import Base


class WasteType(Base):
    __tablename__ = "waste_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    records = relationship("WasteRecord", back_populates="waste_type")


class Material(Base):
    __tablename__ = "materials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    records = relationship("WasteRecord", back_populates="material")


class Machine(Base):
    __tablename__ = "machines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    records = relationship("WasteRecord", back_populates="machine")


class Cause(Base):
    __tablename__ = "causes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    records = relationship("WasteRecord", back_populates="cause")


class QRContext(Base):
    __tablename__ = "qr_contexts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    label = Column(String(100), nullable=True)
    waste_type_id = Column(UUID(as_uuid=True), ForeignKey("waste_types.id"), nullable=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True)
    machine_id = Column(UUID(as_uuid=True), ForeignKey("machines.id"), nullable=True)
    cause_id = Column(UUID(as_uuid=True), ForeignKey("causes.id"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    waste_type = relationship("WasteType")
    material = relationship("Material")
    machine = relationship("Machine")
    cause = relationship("Cause")
    records = relationship("WasteRecord", back_populates="qr_context")


class WasteRecord(Base):
    __tablename__ = "waste_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    waste_type_id = Column(UUID(as_uuid=True), ForeignKey("waste_types.id"), nullable=False, index=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=False, index=True)
    machine_id = Column(UUID(as_uuid=True), ForeignKey("machines.id"), nullable=False, index=True)
    cause_id = Column(UUID(as_uuid=True), ForeignKey("causes.id"), nullable=False, index=True)
    weight_g = Column(Numeric(12, 3), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    qr_context_id = Column(UUID(as_uuid=True), ForeignKey("qr_contexts.id"), nullable=True)
    source = Column(String(20), nullable=False, default="manual")
    idempotency_key = Column(String(100), unique=True, nullable=False, index=True)
    payload_hash = Column(String(64), nullable=False)

    __table_args__ = (
        CheckConstraint("weight_g > 0", name="chk_positive_weight"),
        Index("idx_records_type_date", "waste_type_id", "recorded_at"),
        Index("idx_records_cause_date", "cause_id", "recorded_at"),
    )

    waste_type = relationship("WasteType", back_populates="records")
    material = relationship("Material", back_populates="records")
    machine = relationship("Machine", back_populates="records")
    cause = relationship("Cause", back_populates="records")
    qr_context = relationship("QRContext", back_populates="records")


class ReportRun(Base):
    __tablename__ = "report_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    period = Column(String(7), nullable=False, index=True)  # YYYY-MM
    revision = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="draft")  # draft, completed, failed
    generated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    snapshot = Column(JSONB, nullable=False)
    pdf_path = Column(String(255), nullable=True)
    content_hash = Column(String(64), nullable=True)

    __table_args__ = (
        UniqueConstraint("period", "revision", name="uq_report_period_revision"),
    )

    deliveries = relationship("ReportDelivery", back_populates="report_run", cascade="all, delete-orphan")


class ReportDelivery(Base):
    __tablename__ = "report_deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_run_id = Column(UUID(as_uuid=True), ForeignKey("report_runs.id"), nullable=False, index=True)
    recipient = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending, sending, sent, failed, uncertain
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime(timezone=True), nullable=True)
    error_summary = Column(Text, nullable=True)
    message_id = Column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint("report_run_id", "recipient", name="uq_report_delivery_recipient"),
    )

    report_run = relationship("ReportRun", back_populates="deliveries")

