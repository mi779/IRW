from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from schemas.morpheme import MorphemeRead


class WordBase(BaseModel):
    spelling: str
    phonetics: Optional[dict] = None
    definitions: Optional[list] = None
    part_of_speech: Optional[str] = None
    tags: Optional[List[str]] = None
    example_sentences: Optional[list] = None
    category: Optional[str] = None


class WordCreate(WordBase):
    root_ids: Optional[List[int]] = None
    prefix_ids: Optional[List[int]] = None
    suffix_ids: Optional[List[int]] = None


class WordUpdate(BaseModel):
    spelling: Optional[str] = None
    phonetics: Optional[dict] = None
    definitions: Optional[list] = None
    part_of_speech: Optional[str] = None
    tags: Optional[List[str]] = None
    example_sentences: Optional[list] = None
    category: Optional[str] = None
    root_ids: Optional[List[int]] = None
    prefix_ids: Optional[List[int]] = None
    suffix_ids: Optional[List[int]] = None


class WordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    spelling: str
    phonetics: Optional[dict] = None
    transliteration: Optional[str] = None
    definitions: Optional[list] = None
    part_of_speech: Optional[str] = None
    tags: Optional[List[str]] = None
    bnc: Optional[int] = None
    frq: Optional[int] = None
    example_sentences: Optional[list] = None
    category: Optional[str] = None
    created_at: datetime


class WordReadWithRelations(WordRead):
    roots: List[MorphemeRead] = []
    prefixes: List[MorphemeRead] = []
    suffixes: List[MorphemeRead] = []


class WordPage(BaseModel):
    """Paginated word list (the dictionary has 770k+ entries)."""
    total: int
    items: List[WordReadWithRelations]
    skip: int
    limit: int


class WordRelationRead(BaseModel):
    """One synonym/antonym entry (WordNet)."""
    model_config = ConfigDict(from_attributes=True)

    related_word: str
    relation: str
    pos: Optional[str] = None
    gloss_cn: Optional[str] = None


class WordPhraseRead(BaseModel):
    """One phrase collocation (WordNet multi-word lemma)."""
    model_config = ConfigDict(from_attributes=True)

    phrase: str
    pos: Optional[str] = None
    gloss_cn: Optional[str] = None
    gloss_en: Optional[str] = None


class WordRelated(BaseModel):
    """Extra dictionary data for the word-detail drawer."""
    synonyms: List[WordRelationRead] = []
    antonyms: List[WordRelationRead] = []
    phrases: List[WordPhraseRead] = []
