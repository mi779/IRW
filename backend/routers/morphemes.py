from typing import List, Type

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.morpheme import Prefix, Root, Suffix
from schemas.morpheme import MorphemeCreate, MorphemeRead, MorphemeUpdate

router = APIRouter()


def _build_subrouter(model: Type, prefix: str) -> APIRouter:
    sub = APIRouter(prefix=prefix, tags=[prefix.strip("/")])

    @sub.get("/", response_model=List[MorphemeRead])
    async def list_items(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(model))
        return result.scalars().all()

    @sub.get("/{item_id}", response_model=MorphemeRead)
    async def get_item(item_id: int, db: AsyncSession = Depends(get_db)):
        item = (await db.execute(select(model).where(model.id == item_id))).scalars().first()
        if item is None:
            raise HTTPException(status_code=404, detail=f"{prefix.strip('/')} not found")
        return item

    @sub.post("/", response_model=MorphemeRead, status_code=status.HTTP_201_CREATED)
    async def create_item(payload: MorphemeCreate, db: AsyncSession = Depends(get_db)):
        item = model(text=payload.text, meaning=payload.meaning, description=payload.description)
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    @sub.put("/{item_id}", response_model=MorphemeRead)
    async def update_item(
        item_id: int, payload: MorphemeUpdate, db: AsyncSession = Depends(get_db)
    ):
        item = (await db.execute(select(model).where(model.id == item_id))).scalars().first()
        if item is None:
            raise HTTPException(status_code=404, detail=f"{prefix.strip('/')} not found")
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(item, field, value)
        await db.commit()
        await db.refresh(item)
        return item

    @sub.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_item(item_id: int, db: AsyncSession = Depends(get_db)):
        item = (await db.execute(select(model).where(model.id == item_id))).scalars().first()
        if item is None:
            raise HTTPException(status_code=404, detail=f"{prefix.strip('/')} not found")
        await db.delete(item)
        await db.commit()
        return None

    return sub


router.include_router(_build_subrouter(Root, "/roots"))
router.include_router(_build_subrouter(Prefix, "/prefixes"))
router.include_router(_build_subrouter(Suffix, "/suffixes"))
