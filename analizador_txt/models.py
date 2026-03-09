from pydantic import BaseModel, validator
from typing import Optional


class BaseRecordModel(BaseModel):
    raw_line: str
    row_number: Optional[int]


class MORecordModel(BaseRecordModel):
    # Ejemplo parcial: definir algunos campos como muestra
    field_1: Optional[str] = None
    field_2: Optional[str] = None

    @validator("field_1", pre=True, always=True)
    def strip_field_1(cls, v):
        if v is None:
            return v
        return v.strip()
