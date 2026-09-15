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
    root_ids: Optional[List[int]] = None
    prefix_ids: Optional[List[int]] = None
    suffix_ids: Optional[List[int]] = None


class WordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    spelling: str
    phonetics: Optional[dict] = None
    definitions: Optional[list] = None
    part_of_speech: Optional[str] = None
    tags: Optional[List[str]] = None
    bnc: Optional[int] = None
    frq: Optional[int] = None
    example_sentences: Optional[list] = None
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
