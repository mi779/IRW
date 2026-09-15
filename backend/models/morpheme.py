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

    words: Mapped[List["Word"]] = relationship(
        secondary=word_root, lazy="selectin", back_populates="roots"
    )


class Prefix(TimestampMixin, Base):
    __tablename__ = "prefixes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    meaning: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    words: Mapped[List["Word"]] = relationship(
        secondary=word_prefix, lazy="selectin", back_populates="prefixes"
    )


class Suffix(TimestampMixin, Base):
    __tablename__ = "suffixes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    meaning: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    words: Mapped[List["Word"]] = relationship(
        secondary=word_suffix, lazy="selectin", back_populates="suffixes"
    )


from models.word import Word  # noqa: E402,F401
