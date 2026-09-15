from typing import List

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.associations import word_prefix, word_root, word_suffix
from models.base import TimestampMixin


class Root(TimestampMixin, Base):
    __tablename__ = "roots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    meaning: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Non-column attribute; set by list endpoints for API serialization.
    word_count = None

    # noload: never eager-load linked words. With 770k words / 300k links,
    # selectin here cascaded into loading huge swaths of the dictionary on
    # every morpheme query and timed out API requests. All endpoints that
    # need morpheme-word joins query from the Word side instead.
    words: Mapped[List["Word"]] = relationship(
        secondary=word_root, lazy="noload", back_populates="roots"
    )


class Prefix(TimestampMixin, Base):
    __tablename__ = "prefixes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    meaning: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    word_count = None

    words: Mapped[List["Word"]] = relationship(
        secondary=word_prefix, lazy="noload", back_populates="prefixes"
    )


class Suffix(TimestampMixin, Base):
    __tablename__ = "suffixes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    meaning: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    word_count = None

    words: Mapped[List["Word"]] = relationship(
        secondary=word_suffix, lazy="noload", back_populates="suffixes"
    )


from models.word import Word  # noqa: E402,F401
