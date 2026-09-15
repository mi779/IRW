from typing import Dict, List, Optional

from pydantic import BaseModel


class G6Node(BaseModel):
    id: str
    label: str
    data: Dict


class G6Edge(BaseModel):
    source: str
    target: str
    label: Optional[str] = None


class GraphData(BaseModel):
    nodes: List[G6Node]
    edges: List[G6Edge]
