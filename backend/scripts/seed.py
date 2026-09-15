"""Seed demo data: morpheme families (spect/port/dict/vis) for group learning.

Idempotent: existing morphemes/words are skipped, so the script can be
re-run safely.

Usage (from backend/):
    python scripts/seed.py
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session
from models.morpheme import Prefix, Root, Suffix
from models.word import Word

ROOTS = [
    {
        "text": "spect",
        "meaning": "看",
        "description": "拉丁词根，来自 spectare（看）。同族词多与“看、观察”相关。",
    },
    {
        "text": "port",
        "meaning": "拿；运",
        "description": "拉丁词根，来自 portare（搬运）。同族词多与“运输、携带”相关。",
    },
    {
        "text": "dict",
        "meaning": "说",
        "description": "拉丁词根，来自 dicere（说）。同族词多与“说话、言辞”相关。",
    },
    {
        "text": "vis",
        "meaning": "看",
        "description": "拉丁词根，来自 videre（看）。同族词多与“看见、视觉”相关。",
    },
]

PREFIXES = [
    {"text": "in", "meaning": "向内", "description": "如 inspect：向内看 → 检查。"},
    {
        "text": "im",
        "meaning": "进入",
        "description": "in- 在 b/m/p 前的变体。如 import：运进来 → 进口。",
    },
    {"text": "re", "meaning": "再次；回", "description": "如 respect：反复看 → 尊敬。"},
    {"text": "pro", "meaning": "向前", "description": "如 prospect：向前看 → 前景。"},
    {
        "text": "sub",
        "meaning": "在下面",
        "description": "如 suspect：从下面偷偷看 → 怀疑。",
    },
    {"text": "per", "meaning": "透过；彻底", "description": "如 perspective：透过去看 → 视角。"},
    {"text": "ex", "meaning": "向外", "description": "如 export：运出去 → 出口。"},
    {"text": "pre", "meaning": "提前", "description": "如 predict：提前说 → 预测。"},
    {"text": "contra", "meaning": "相反", "description": "如 contradict：反着说 → 反驳。"},
]

SUFFIXES = [
    {"text": "-or", "meaning": "名词后缀：…的人", "description": "如 spectator：看的人 → 观众。"},
    {"text": "-able", "meaning": "形容词后缀：可…的", "description": "如 portable：可搬运的 → 便携的。"},
    {"text": "-ive", "meaning": "形容词后缀：有…性质的", "description": "如 perspective：视角的。"},
    {"text": "-ible", "meaning": "形容词后缀：可…的", "description": "如 visible：可看见的。"},
]

WORDS = [
    {
        "spelling": "inspect",
        "phonetics": {"us": "/ɪnˈspekt/", "uk": "/ɪnˈspekt/"},
        "definitions": [{"pos": "v.", "text": "检查；视察"}],
        "part_of_speech": "v.",
        "example_sentences": ["The customs officer inspected my luggage."],
        "roots": ["spect"],
        "prefixes": ["in"],
        "suffixes": [],
    },
    {
        "spelling": "respect",
        "phonetics": {"us": "/rɪˈspekt/", "uk": "/rɪˈspekt/"},
        "definitions": [{"pos": "n.", "text": "尊敬；尊重"}, {"pos": "v.", "text": "尊敬；尊重"}],
        "part_of_speech": "n./v.",
        "example_sentences": ["We should respect our teachers."],
        "roots": ["spect"],
        "prefixes": ["re"],
        "suffixes": [],
    },
    {
        "spelling": "spectator",
        "phonetics": {"us": "/ˈspekteɪtər/", "uk": "/ˈspekteɪtə(r)/"},
        "definitions": [{"pos": "n.", "text": "观众；旁观者"}],
        "part_of_speech": "n.",
        "example_sentences": ["Thousands of spectators watched the final game."],
        "roots": ["spect"],
        "prefixes": [],
        "suffixes": ["-or"],
    },
    {
        "spelling": "prospect",
        "phonetics": {"us": "/ˈprɑːspekt/", "uk": "/ˈprɒspekt/"},
        "definitions": [{"pos": "n.", "text": "前景；展望；可能性"}],
        "part_of_speech": "n.",
        "example_sentences": ["The job offers good career prospects."],
        "roots": ["spect"],
        "prefixes": ["pro"],
        "suffixes": [],
    },
    {
        "spelling": "suspect",
        "phonetics": {"us": "/səˈspekt/", "uk": "/səˈspekt/"},
        "definitions": [{"pos": "v.", "text": "怀疑；猜想"}, {"pos": "n.", "text": "嫌疑人"}],
        "part_of_speech": "v./n.",
        "example_sentences": ["I suspect that he is lying."],
        "roots": ["spect"],
        "prefixes": ["sub"],
        "suffixes": [],
    },
    {
        "spelling": "perspective",
        "phonetics": {"us": "/pərˈspektɪv/", "uk": "/pəˈspektɪv/"},
        "definitions": [{"pos": "n.", "text": "观点；视角；透视法"}],
        "part_of_speech": "n.",
        "example_sentences": ["Try to see things from my perspective."],
        "roots": ["spect"],
        "prefixes": ["per"],
        "suffixes": ["-ive"],
    },
    {
        "spelling": "import",
        "phonetics": {"us": "/ɪmˈpɔːrt/", "uk": "/ɪmˈpɔːt/"},
        "definitions": [{"pos": "v.", "text": "进口；输入"}, {"pos": "n.", "text": "进口；进口货"}],
        "part_of_speech": "v./n.",
        "example_sentences": ["The country imports most of its oil."],
        "roots": ["port"],
        "prefixes": ["im"],
        "suffixes": [],
    },
    {
        "spelling": "export",
        "phonetics": {"us": "/ɪkˈspɔːrt/", "uk": "/ɪkˈspɔːt/"},
        "definitions": [{"pos": "v.", "text": "出口；输出"}, {"pos": "n.", "text": "出口；出口货"}],
        "part_of_speech": "v./n.",
        "example_sentences": ["Brazil exports coffee to many countries."],
        "roots": ["port"],
        "prefixes": ["ex"],
        "suffixes": [],
    },
    {
        "spelling": "portable",
        "phonetics": {"us": "/ˈpɔːrtəbl/", "uk": "/ˈpɔːtəbl/"},
        "definitions": [{"pos": "adj.", "text": "便携的；轻便的"}],
        "part_of_speech": "adj.",
        "example_sentences": ["I bought a portable Bluetooth speaker."],
        "roots": ["port"],
        "prefixes": [],
        "suffixes": ["-able"],
    },
    {
        "spelling": "predict",
        "phonetics": {"us": "/prɪˈdɪkt/", "uk": "/prɪˈdɪkt/"},
        "definitions": [{"pos": "v.", "text": "预测；预言"}],
        "part_of_speech": "v.",
        "example_sentences": ["No one can predict the future accurately."],
        "roots": ["dict"],
        "prefixes": ["pre"],
        "suffixes": [],
    },
    {
        "spelling": "contradict",
        "phonetics": {"us": "/ˌkɑːntrəˈdɪkt/", "uk": "/ˌkɒntrəˈdɪkt/"},
        "definitions": [{"pos": "v.", "text": "反驳；与…相矛盾"}],
        "part_of_speech": "v.",
        "example_sentences": ["The two reports contradict each other."],
        "roots": ["dict"],
        "prefixes": ["contra"],
        "suffixes": [],
    },
    {
        "spelling": "revise",
        "phonetics": {"us": "/rɪˈvaɪz/", "uk": "/rɪˈvaɪz/"},
        "definitions": [{"pos": "v.", "text": "修订；修改；复习"}],
        "part_of_speech": "v.",
        "example_sentences": ["I need to revise my essay before submitting it."],
        "roots": ["vis"],
        "prefixes": ["re"],
        "suffixes": [],
    },
    {
        "spelling": "visible",
        "phonetics": {"us": "/ˈvɪzəbl/", "uk": "/ˈvɪzəbl/"},
        "definitions": [{"pos": "adj.", "text": "看得见的；明显的"}],
        "part_of_speech": "adj.",
        "example_sentences": ["The stars are clearly visible tonight."],
        "roots": ["vis"],
        "prefixes": [],
        "suffixes": ["-ible"],
    },
]


async def _get_or_create_morpheme(
    db: AsyncSession, model, data: dict
) -> Optional[object]:
    item = (
        (await db.execute(select(model).where(model.text == data["text"])))
        .scalars()
        .first()
    )
    if item is None:
        item = model(**data)
        db.add(item)
        await db.flush()
    return item


async def main() -> None:
    async with async_session() as db:
        roots: dict = {}
        for r in ROOTS:
            roots[r["text"]] = await _get_or_create_morpheme(db, Root, r)
        prefixes: dict = {}
        for p in PREFIXES:
            prefixes[p["text"]] = await _get_or_create_morpheme(db, Prefix, p)
        suffixes: dict = {}
        for s in SUFFIXES:
            suffixes[s["text"]] = await _get_or_create_morpheme(db, Suffix, s)

        created, skipped = 0, 0
        for w in WORDS:
            existing = (
                await db.execute(select(Word).where(Word.spelling == w["spelling"]))
            ).scalars()
            if existing.first() is not None:
                skipped += 1
                continue
            word = Word(
                spelling=w["spelling"],
                phonetics=w["phonetics"],
                definitions=w["definitions"],
                part_of_speech=w["part_of_speech"],
                example_sentences=w["example_sentences"],
            )
            db.add(word)
            await db.flush()
            word = (
                (await db.execute(select(Word).where(Word.spelling == w["spelling"])))
                .scalars()
                .first()
            )
            word.roots = [roots[t] for t in w["roots"]]
            word.prefixes = [prefixes[t] for t in w["prefixes"]]
            word.suffixes = [suffixes[t] for t in w["suffixes"]]
            created += 1

        await db.commit()
        print(
            f"Seed done: {len(ROOTS)} roots, {len(PREFIXES)} prefixes, "
            f"{len(SUFFIXES)} suffixes; words created={created}, skipped={skipped}."
        )


if __name__ == "__main__":
    asyncio.run(main())
