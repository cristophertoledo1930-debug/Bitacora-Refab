from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class CatalogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str


class CatalogsResponse(BaseModel):
    waste_types: list[CatalogItem]
    materials: list[CatalogItem]
    machines: list[CatalogItem]
    causes: list[CatalogItem]


class WasteRecordCreate(BaseModel):
    qr_token: str | None = None
    waste_type_id: UUID
    material_id: UUID
    machine_id: UUID
    cause_id: UUID
    weight: str = Field(..., description="Peso expresado en formato texto decimal")
    unit: str = Field(default="g", description="'g' o 'kg'")
    source: str = Field(default="manual")


class WasteRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    recorded_at: datetime
    weight_g: Decimal
    waste_type_id: UUID
    material_id: UUID
    machine_id: UUID
    cause_id: UUID
    source: str
    idempotency_key: str

