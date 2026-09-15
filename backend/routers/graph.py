from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.morpheme import Prefix, Root, Suffix
from schemas.graph import G6Edge, G6Node, GraphData

router = APIRouter()


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


@router.get("/root/{root_id}", response_model=GraphData)
async def graph_by_root(root_id: int, db: AsyncSession = Depends(get_db)):
    root = (await db.execute(select(Root).where(Root.id == root_id))).scalars().first()
    if root is None:
        raise HTTPException(status_code=404, detail="Root not found")
    return _build_graph_for_morpheme(root, "root", root.words)


@router.get("/prefix/{prefix_id}", response_model=GraphData)
async def graph_by_prefix(prefix_id: int, db: AsyncSession = Depends(get_db)):
    prefix = (await db.execute(select(Prefix).where(Prefix.id == prefix_id))).scalars().first()
    if prefix is None:
        raise HTTPException(status_code=404, detail="Prefix not found")
    return _build_graph_for_morpheme(prefix, "prefix", prefix.words)


@router.get("/suffix/{suffix_id}", response_model=GraphData)
async def graph_by_suffix(suffix_id: int, db: AsyncSession = Depends(get_db)):
    suffix = (await db.execute(select(Suffix).where(Suffix.id == suffix_id))).scalars().first()
    if suffix is None:
        raise HTTPException(status_code=404, detail="Suffix not found")
    return _build_graph_for_morpheme(suffix, "suffix", suffix.words)
