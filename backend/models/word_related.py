"""WordNet-derived extra data: synonyms/antonyms and phrase collocations."""

from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from models.base import TimestampMixin


class WordRelation(TimestampMixin, Base):
    """Synonym / antonym links between a word and related spellings.

    Data source: WordNet 3.1 synsets (synonyms) and `!` lexical pointers
    (antonyms). `related_word` is stored as spelling text instead of a FK so
    relations to words outside our dictionary stay intact.
    """

    __tablename__ = "word_relations"
    __table_args__ = (
        UniqueConstraint("word_id", "relation", "related_word", name="uq_word_relation"),
        {"comment": "WordNet synonyms/antonyms per word"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id", ondelete="CASCADE"), nullable=False, index=True
    )
    related_word: Mapped[str] = mapped_column(String(100), nullable=False)
    relation: Mapped[str] = mapped_column(String(10), nullable=False)  # synonym|antonym
    pos: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)  # n|v|a|r
    # Lower = more frequent sense (order in WordNet index file).
    sense_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Chinese gloss of related_word, backfilled from the words table.
    gloss_cn: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class WordPhrase(TimestampMixin, Base):
    """Multi-word lemmas (phrasal verbs, compounds) attached to their
    component words, e.g. "look after" -> look; "take care of" -> take, care."""

    __tablename__ = "word_phrases"
    __table_args__ = (
        UniqueConstraint("word_id", "phrase", name="uq_word_phrase"),
        {"comment": "WordNet multi-word lemmas as collocations"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id", ondelete="CASCADE"), nullable=False, index=True
    )
    phrase: Mapped[str] = mapped_column(String(120), nullable=False)
    pos: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)  # n|v|a|r
    gloss_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # WordNet gloss
    gloss_cn: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # from words table
    sense_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
