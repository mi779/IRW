from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.morpheme import Prefix, Root, Suffix
from models.word import Word
from schemas.graph import G6Edge, G6Node, GraphData

router = APIRouter()


def _frequency_order():
    """Order words by contemporary-corpus frequency (smaller = more common).
    Words without frequency data (NULL or 0) go last."""
    return func.coalesce(func.nullif(Word.frq, 0), 999999), Word.spelling


def _build_graph_for_morpheme(morpheme, morpheme_type: str, words) -> GraphData:
    morpheme_node_id = f"{morpheme_type}:{morpheme.id}"
    nodes = [
        G6Node(
            id=morpheme_node_id,
            label=f"{morpheme.text} ({morpheme.meaning})",
            data={
                "type": morpheme_type,
                "id": morpheme.id,
                "text": morpheme.text,
                "meaning": morpheme.meaning,
            },
        )
    ]
    edges = []
    for word in words:
        word_node_id = f"word:{word.id}"
        nodes.append(
            G6Node(
                id=word_node_id,
                label=word.spelling,
                data={"type": "word", "id": word.id, "spelling": word.spelling},
            )
        )
        edges.append(G6Edge(source=word_node_id, target=morpheme_node_id))
    return GraphData(nodes=nodes, edges=edges)


async def _graph_for_morpheme(
    db: AsyncSession, model, morpheme_type: str, morpheme_id: int, limit: int
) -> GraphData:
    morpheme = (
        await db.execute(select(model).where(model.id == morpheme_id))
    ).scalars().first()
    if morpheme is None:
        raise HTTPException(status_code=404, detail=f"{morpheme_type} not found")
    words = (
        await db.execute(
            select(Word)
            .join(Word.roots if model is Root else Word.prefixes if model is Prefix else Word.suffixes)
            .where(model.id == morpheme_id)
            .order_by(*_frequency_order())
            .limit(limit)
        )
    ).scalars().all()
    return _build_graph_for_morpheme(morpheme, morpheme_type, words)


@router.get("/root/{root_id}", response_model=GraphData)
async def graph_by_root(
    root_id: int,
    limit: int = Query(60, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    return await _graph_for_morpheme(db, Root, "root", root_id, limit)


@router.get("/prefix/{prefix_id}", response_model=GraphData)
async def graph_by_prefix(
    prefix_id: int,
    limit: int = Query(60, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    return await _graph_for_morpheme(db, Prefix, "prefix", prefix_id, limit)


@router.get("/suffix/{suffix_id}", response_model=GraphData)
async def graph_by_suffix(
    suffix_id: int,
    limit: int = Query(60, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    return await _graph_for_morpheme(db, Suffix, "suffix", suffix_id, limit)
