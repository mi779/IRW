from typing import Optional

from pydantic import BaseModel, ConfigDict


class MorphemeBase(BaseModel):
    text: str
    meaning: Optional[str] = None
    description: Optional[str] = None


class MorphemeCreate(MorphemeBase):
    pass


class MorphemeUpdate(BaseModel):
    text: Optional[str] = None
    meaning: Optional[str] = None
    description: Optional[str] = None


class MorphemeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    meaning: Optional[str] = None
    description: Optional[str] = None
    # Word count is attached by the list endpoints (not a DB column).
    word_count: Optional[int] = None
