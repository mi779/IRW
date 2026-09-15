from sqlalchemy import Column, ForeignKey, Index, Integer, Table

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
    # Reverse lookup: all words of a root. The composite PK (word_id, morpheme_id)
    # does not cover queries filtered only by morpheme_id.
    Index("idx_word_root_morpheme", "morpheme_id"),
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
    Index("idx_word_prefix_morpheme", "morpheme_id"),
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
    Index("idx_word_suffix_morpheme", "morpheme_id"),
)
