from sqlalchemy import Column, ForeignKey, Integer, Table

from core.database import Base

word_root = Table(
    "word_root",
    Base.metadata,
    Column(
        "word_id",
        Integer,
        ForeignKey("words.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "morpheme_id",
        Integer,
        ForeignKey("roots.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

word_prefix = Table(
    "word_prefix",
    Base.metadata,
    Column(
        "word_id",
        Integer,
        ForeignKey("words.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "morpheme_id",
        Integer,
        ForeignKey("prefixes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

word_suffix = Table(
    "word_suffix",
    Base.metadata,
    Column(
        "word_id",
        Integer,
        ForeignKey("words.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "morpheme_id",
        Integer,
        ForeignKey("suffixes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
