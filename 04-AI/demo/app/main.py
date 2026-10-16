"""
FastAPI service for the log analyst.

Run:   cd demo && ../../../ai/labs/.venv/bin/uvicorn app.main:app --port 8000
       (or from notebook 06)
"""
import re
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from logbot.chat import ChatV1
from logbot.llm import LocalLLM
from logbot.parse import read_logs
from logbot.rag import AskV2, RagIndex
from logbot.tools import summary

STATE = {}


@asynccontextmanager
async def lifespan(app):
    t0 = time.perf_counter()
    df = read_logs()
    try:
        index = RagIndex.load()
    except FileNotFoundError:
        index = RagIndex.build(df)
        index.save()
    llm = LocalLLM()
    STATE.update(df=df, index=index, llm=llm, v1=ChatV1(llm, df), v2=AskV2(llm, index, df),
                 started=round(time.perf_counter() - t0, 1))
    yield
    STATE.clear()


app = FastAPI(title='Log analyst (Apache + Java)', version='1.0', lifespan=lifespan)


class ChatIn(BaseModel):
    session_id: str = Field('default', max_length=64)
    message: str = Field(..., min_length=2, max_length=500)


class AskIn(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)
    file: str | None = Field(None, description='only search this log file, e.g. app/application.log')
    since: str | None = Field(None, description='e.g. 2026-10-14 08:00')
    until: str | None = Field(None, description='e.g. 2026-10-14 12:00')


class IngestIn(BaseModel):
    name: str = Field(..., pattern=r'^[\w./-]{1,80}$')
    text: str = Field(..., min_length=1, max_length=200_000)


def ready():
    if 'v2' not in STATE:
        raise HTTPException(503, 'still loading')


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.get('/ready')
def is_ready():
    ready()
    return {'status': 'ready', 'model': STATE['llm'].model_id, 'device': STATE['llm'].device,
            'chunks': len(STATE['index'].chunks), 'startup_seconds': STATE['started']}


@app.get('/stats')
def stats():
    ready()
    return summary(STATE['df'])


@app.post('/v1/chat')
def chat_v1(body: ChatIn):
    ready()
    t0 = time.perf_counter()
    answer, s = STATE['v1'].ask(body.message, body.session_id)
    return {'version': 'v1', 'session_id': body.session_id, 'answer': answer,
            'latency_ms': round((time.perf_counter() - t0) * 1000), 'tokens': s}


@app.post('/v2/ask')
def ask_v2(body: AskIn):
    ready()
    t0 = time.perf_counter()
    answer, sources, s = STATE['v2'].ask(body.question, file=body.file, since=body.since, until=body.until)
    return {'version': 'v2', 'answer': answer, 'sources': sources,
            'latency_ms': round((time.perf_counter() - t0) * 1000), 'tokens': s}


@app.post('/v2/ingest')
def ingest(body: IngestIn):
    """Add new log text: split into blocks of 20 lines, embed, and make them searchable at once."""
    ready()
    lines = body.text.splitlines()
    chunks = []
    for i in range(0, len(lines), 20):
        block = lines[i:i + 20]
        stamp = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', ' '.join(block))
        chunks.append(dict(kind='log', file=f'ingested/{body.name}', start=stamp[0] if stamp else '', line=i + 1,
                           text=f'ingested/{body.name} lines {i + 1}-{i + len(block)}:\n' + '\n'.join(block)))
    STATE['index'].add(chunks)
    return {'added_chunks': len(chunks), 'total_chunks': len(STATE['index'].chunks)}
