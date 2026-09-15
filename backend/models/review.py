from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.base import TimestampMixin


class ReviewLog(TimestampMixin, Base):
    __tablename__ = "review_logs"
    __table_args__ = (
        # Composite index for "latest review per word" subquery.
        Index("idx_review_logs_word_review_date", "word_id", "review_date"),
        # Index for due-queue filtering (due_date <= now).
        Index("idx_review_logs_due_date", "due_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("words.id", ondelete="CASCADE"), nullable=False
    )
    review_date: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    quality: Mapped[int] = mapped_column(Integer, nullable=False)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    repetitions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    word: Mapped[Optional["Word"]] = relationship(back_populates="review_logs")


from models.word import Word  # noqa: E402,F401
