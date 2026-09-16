"""Pipeline-imported auxiliary data: word forms, etymology, source registry."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CHAR,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from models.base import TimestampMixin


class WordForm(TimestampMixin, Base):
    """Inflected forms of a word (词形变化).

    Data sources: ECDICT `exchange` field (Chinese tags: 过去式/过去分词/...)
    and Wiktionary/Kaikki `forms` (English tags: plural/past/...).
    """

    __tablename__ = "word_forms"
    __table_args__ = (
        UniqueConstraint("word_id", "form", name="uq_word_form"),
        {"comment": "词形变化(来自ECDICT exchange与Kaikki forms)"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id", ondelete="CASCADE"), nullable=False, index=True
    )
    form: Mapped[str] = mapped_column(String(150), nullable=False)
    form_tags: Mapped[Optional[str]] = mapped_column(String(190), nullable=True)
    # ecdict | kaikki
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="ecdict")


class WordEtymology(TimestampMixin, Base):
    """Etymology text of a word (词源), from Wiktionary/Kaikki."""

    __tablename__ = "word_etymologies"
    __table_args__ = (
        UniqueConstraint("word_id", name="uq_word_etymology"),
        {"comment": "词源文本(来自Kaikki etymology_text)"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id", ondelete="CASCADE"), nullable=False
    )
    etymology_text: Mapped[Optional[str]] = mapped_column(MEDIUMTEXT, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="kaikki")


class PipelineSource(TimestampMixin, Base):
    """Data source registry written by the import pipeline (来源清单).

    Stable identity = source_key; re-imports refresh sha256/version/license.
    Populated from data/pipeline/downloads/manifest.json.
    """

    __tablename__ = "pipeline_sources"
    __table_args__ = {"comment": "词库数据来源记录(manifest)"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    page_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[Optional[str]] = mapped_column(CHAR(64), nullable=True)
    data_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    license: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
