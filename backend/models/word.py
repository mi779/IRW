from typing import List, Optional

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.associations import word_prefix, word_root, word_suffix
from models.base import TimestampMixin


class Word(TimestampMixin, Base):
    __tablename__ = "words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spelling: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    phonetics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    transliteration: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    definitions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    part_of_speech: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    bnc: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    frq: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    example_sentences: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # 词条类别(来自 Wiktionary/Kaikki 解析): lemma/inflection/phrase/proper_noun/
    # abbreviation/symbol/archaic/rare/morpheme, 见 pipeline/parse_kaikki.py
    category: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    roots: Mapped[List["Root"]] = relationship(
        secondary=word_root, lazy="selectin", back_populates="words"
    )
    prefixes: Mapped[List["Prefix"]] = relationship(
        secondary=word_prefix, lazy="selectin", back_populates="words"
    )
    suffixes: Mapped[List["Suffix"]] = relationship(
        secondary=word_suffix, lazy="selectin", back_populates="words"
    )

    # noload: review queries go through ReviewLog directly; eager-loading
    # logs for every fetched word ballooned word queries unnecessarily.
    review_logs: Mapped[List["ReviewLog"]] = relationship(
        back_populates="word", lazy="noload"
    )


# Avoid circular imports at type-check time.
from models.morpheme import Prefix, Root, Suffix  # noqa: E402,F401
from models.review import ReviewLog  # noqa: E402,F401
