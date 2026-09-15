from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas.review import ReviewLogCreate, ReviewLogRead, ReviewQueueItem
from services.review_service import apply_review, get_due_queue

router = APIRouter()


@router.get("/queue", response_model=List[ReviewQueueItem])
async def queue(limit: int = 20, db: AsyncSession = Depends(get_db)):
    items = await get_due_queue(db, limit=limit)
    return items


@router.post("/log", response_model=ReviewLogRead)
async def log_review(payload: ReviewLogCreate, db: AsyncSession = Depends(get_db)):
    log = await apply_review(db, word_id=payload.word_id, quality=payload.quality)
    return log
