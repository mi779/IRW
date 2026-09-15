"""Create the vocab_app database and sync all tables/indexes to MySQL.

Usage (from backend/):
    python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from core.config import settings


async def main() -> None:
    url = make_url(settings.database_url)
    db_name = url.database

    # 1. Ensure the database exists (utf8mb4 for full Unicode support).
    # Note: URL.set(database=None) is a no-op in SQLAlchemy 2.0, so build a
    # server-level URL explicitly.
    server_url = URL.create(
        drivername=url.drivername,
        username=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        query=dict(url.query),
    )
    server_engine = create_async_engine(server_url, isolation_level="AUTOCOMMIT")
    async with server_engine.connect() as conn:
        await conn.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS {db_name} "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
    await server_engine.dispose()
    print(f"[1/2] Database `{db_name}` ready (utf8mb4).")

    # 2. Create all tables & indexes declared in models.
    import models  # noqa: F401  (registers all tables on Base.metadata)
    from core.database import Base, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print(f"[2/2] {len(Base.metadata.tables)} tables synced: {sorted(Base.metadata.tables)}")


if __name__ == "__main__":
    asyncio.run(main())
