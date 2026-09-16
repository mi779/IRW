from sqlalchemy import Column, ForeignKey, Index, Integer, String, Table

from core.database import Base


def _link_columns(fk_table: str) -> list:
    """word_id + morpheme_id plus provenance columns filled by the pipeline.

    The ORM never writes the provenance columns (links created through the
    API get NULL evidence with source left at its default), but the data
    pipeline records the Wiktionary template each link came from.
    """
    return [
        Column(
            "word_id",
            Integer,
            ForeignKey("words.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        Column(
            "morpheme_id",
            Integer,
            ForeignKey(f"{fk_table}.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        Column("evidence", String(300), nullable=True),
        Column("source", String(20), nullable=False, server_default="manual"),
    ]


word_root = Table(
    "word_root",
    Base.metadata,
    *_link_columns("roots"),
    # Reverse lookup: all words of a root. The composite PK (word_id, morpheme_id)
    # does not cover queries filtered only by morpheme_id.
    Index("idx_word_root_morpheme", "morpheme_id"),
)

word_prefix = Table(
    "word_prefix",
    Base.metadata,
    *_link_columns("prefixes"),
    Index("idx_word_prefix_morpheme", "morpheme_id"),
)

word_suffix = Table(
    "word_suffix",
    Base.metadata,
    *_link_columns("suffixes"),
    Index("idx_word_suffix_morpheme", "morpheme_id"),
)
