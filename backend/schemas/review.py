from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ReviewLogCreate(BaseModel):
    word_id: int
    quality: int = Field(..., ge=0, le=5)


class ReviewLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    word_id: int
    review_date: datetime
    quality: int
    ease_factor: float
    interval_days: int
    repetitions: int
    due_date: datetime


class ReviewQueueItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    word_id: int
    spelling: str
    due_date: datetime
    ease_factor: float
    repetitions: int
