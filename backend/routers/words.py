from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.morpheme import Prefix, Root, Suffix
from models.word import Word
from schemas.word import (
    WordCreate,
    WordPage,
    WordReadWithRelations,
    WordUpdate,
)

router = APIRouter()


async def _set_morpheme_relations(db: AsyncSession, word: Word, data: WordCreate | WordUpdate) -> None:
    if data.root_ids is not None:
        word.roots = (
            (await db.execute(select(Root).where(Root.id.in_(data.root_ids))))
            .scalars()
            .all()
        )
    if data.prefix_ids is not None:
        word.prefixes = (
            (await db.execute(select(Prefix).where(Prefix.id.in_(data.prefix_ids))))
            .scalars()
            .all()
        )
    if data.suffix_ids is not None:
        word.suffixes = (
            (await db.execute(select(Suffix).where(Suffix.id.in_(data.suffix_ids))))
            .scalars()
            .all()
        )


@router.post("/", response_model=WordReadWithRelations, status_code=status.HTTP_201_CREATED)
async def create_word(payload: WordCreate, db: AsyncSession = Depends(get_db)):
    word = Word(
        spelling=payload.spelling,
        phonetics=payload.phonetics,
        definitions=payload.definitions,
        part_of_speech=payload.part_of_speech,
        example_sentences=payload.example_sentences,
    )
    db.add(word)
    await db.flush()  # assign primary key
    # Re-query so the lazy="selectin" relationship collections are initialized
    # (empty for a new word). Otherwise assigning to word.roots below would
    # trigger a lazy-load of the "old" value and raise MissingGreenlet under
    # an async session.
    word = (await db.execute(select(Word).where(Word.id == word.id))).scalars().first()
    await _set_morpheme_relations(db, word, payload)
    await db.commit()
    return word


@router.get("/", response_model=WordPage)
async def list_words(
    search: str = Query("", max_length=100, description="Fuzzy match on spelling"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Paginated word list. The dictionary holds 770k+ entries, so the
    response is always capped by `limit` (max 200)."""
    stmt = select(Word).order_by(Word.spelling)
    if search:
        stmt = stmt.where(Word.spelling.like(f"%{search}%"))
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    items = (await db.execute(stmt.offset(skip).limit(limit))).scalars().all()
    return WordPage(total=total, items=items, skip=skip, limit=limit)


@router.get("/by-root/{root_id}", response_model=WordPage)
async def words_by_root(
    root_id: int,
    search: str = Query("", max_length=100, description="Fuzzy match on spelling"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Paginated words linked to a root, most frequent first. Some roots
    have thousands of linked words, so the response is always capped by
    `limit` (max 200) and supports spelling search for quick lookup."""
    stmt = (
        select(Word)
        .join(Word.roots)
        .where(Root.id == root_id)
        .order_by(func.coalesce(func.nullif(Word.frq, 0), 999999), Word.spelling)
    )
    if search:
        stmt = stmt.where(Word.spelling.like(f"%{search}%"))
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    items = (await db.execute(stmt.offset(skip).limit(limit))).scalars().all()
    return WordPage(total=total, items=items, skip=skip, limit=limit)


@router.get("/by-prefix/{prefix_id}", response_model=List[WordReadWithRelations])
async def words_by_prefix(
    prefix_id: int,
    limit: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Word)
        .join(Word.prefixes)
        .where(Prefix.id == prefix_id)
        .order_by(func.coalesce(func.nullif(Word.frq, 0), 999999), Word.spelling)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{word_id}", response_model=WordReadWithRelations)
async def get_word(word_id: int, db: AsyncSession = Depends(get_db)):
    word = (await db.execute(select(Word).where(Word.id == word_id))).scalars().first()
    if word is None:
        raise HTTPException(status_code=404, detail="Word not found")
    return word


@router.put("/{word_id}", response_model=WordReadWithRelations)
async def update_word(word_id: int, payload: WordUpdate, db: AsyncSession = Depends(get_db)):
    word = (await db.execute(select(Word).where(Word.id == word_id))).scalars().first()
    if word is None:
        raise HTTPException(status_code=404, detail="Word not found")

    update_data = payload.model_dump(exclude_unset=True)
    morpheme_fields = {"root_ids", "prefix_ids", "suffix_ids"}
    scalar_fields = {k: v for k, v in update_data.items() if k not in morpheme_fields}
    for field, value in scalar_fields.items():
        setattr(word, field, value)

    await _set_morpheme_relations(db, word, payload)
    await db.commit()
    # Re-query so the selectin relationships are loaded for the response.
    result = await db.execute(select(Word).where(Word.id == word_id))
    return result.scalars().first()


@router.delete("/{word_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_word(word_id: int, db: AsyncSession = Depends(get_db)):
    word = (await db.execute(select(Word).where(Word.id == word_id))).scalars().first()
    if word is None:
        raise HTTPException(status_code=404, detail="Word not found")
    await db.delete(word)
    await db.commit()
    return None
