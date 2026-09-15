import os
import subprocess
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import init_db
from routers import graph, morphemes, review, words

START_TIME = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _git_commit() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                stderr=subprocess.DEVNULL,
                timeout=3,
            )
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


COMMIT = _git_commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Vocab App API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(words.router, prefix="/api/words", tags=["words"])
app.include_router(morphemes.router, prefix="/api", tags=["morphemes"])
app.include_router(review.router, prefix="/api/review", tags=["review"])
app.include_router(graph.router, prefix="/api/graph", tags=["graph"])


@app.get("/")
async def root():
    return {"message": "Vocab App API is running"}


@app.get("/api/version")
async def version():
    return {"commit": COMMIT, "started": START_TIME}
