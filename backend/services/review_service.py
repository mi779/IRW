from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.review import ReviewLog
from models.word import Word
from services.sm2 import sm2_update


async def apply_review(
    db: AsyncSession, word_id: int, quality: int
) -> ReviewLog:
    """Apply an SM-2 review for the given word and persist a new ReviewLog."""
    latest: Optional[ReviewLog] = (
        await db.execute(
            select(ReviewLog)
            .where(ReviewLog.word_id == word_id)
            .order_by(desc(ReviewLog.review_date))
            .limit(1)
        )
    ).scalars().first()

    prev_ease = latest.ease_factor if latest else 2.5
    prev_interval = latest.interval_days if latest else 0
    prev_repetitions = latest.repetitions if latest else 0

    result = sm2_update(
        quality=quality,
        prev_ease=prev_ease,
        prev_interval=prev_interval,
        prev_repetitions=prev_repetitions,
    )

    now = datetime.utcnow()
    log = ReviewLog(
        word_id=word_id,
        review_date=now,
        quality=quality,
        ease_factor=result.ease_factor,
        interval_days=result.interval_days,
        repetitions=result.repetitions,
        due_date=now + timedelta(days=result.due_offset_days),
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_due_queue(db: AsyncSession, limit: int = 20) -> List[ReviewLog]:
    """Return words whose latest review is due now, newest-first by due date.

    SQLite does not support DISTINCT ON, so we use a max(review_date)
    subquery to identify the latest review per word.
    """
    latest_dates = (
        select(
            ReviewLog.word_id,
            func.max(ReviewLog.review_date).label("max_date"),
        )
        .group_by(ReviewLog.word_id)
        .subquery()
    )

    now = datetime.utcnow()
    stmt = (
        select(ReviewLog, Word.spelling)
        .join(latest_dates, ReviewLog.word_id == latest_dates.c.word_id)
        .where(ReviewLog.review_date == latest_dates.c.max_date)
        .join(Word, Word.id == ReviewLog.word_id)
        .where(ReviewLog.due_date <= now)
        .order_by(ReviewLog.due_date.asc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    # Return ReviewLog instances; attach spelling for convenience.
    results: List[ReviewLog] = []
    for review_log, spelling in rows:
        # Stash spelling on the instance for schema serialization.
        review_log.spelling = spelling  # type: ignore[attr-defined]
        results.append(review_log)
    return results
