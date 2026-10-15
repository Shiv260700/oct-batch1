"""Text-generation API: give a topic and the start of a post, get the continuation.

GET  /health     liveness  ("the process is up")
GET  /ready      readiness ("the model is loaded")
GET  /topics     the topics you can ask for
POST /generate   {"topic": "space", "prompt": "The shuttle", "max_chars": 200, "temperature": 0.8, "seed": 1}
"""
import logging
import os
import socket
import time

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from textgen.model import load

torch.set_num_threads(int(os.environ.get("TORCH_THREADS", "1")))
MODEL_DIR = os.environ.get("MODEL_DIR", "/app/model")
VERSION = os.environ.get("MODEL_VERSION", "v1")
MAX_CHARS = int(os.environ.get("MAX_CHARS_LIMIT", "500"))
POD = socket.gethostname()
log = logging.getLogger("textgen")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

t0 = time.time()
model, tok, meta = load(MODEL_DIR, "cpu")            # load once at start-up, never per request
LOAD_SECONDS = round(time.time() - t0, 2)
TOPICS = model.config.topics
log.info("model %s loaded in %ss: topics=%s best_step=%s", VERSION, LOAD_SECONDS, TOPICS, meta.get("step"))

app = FastAPI(title="Text generator", version=VERSION)


class Request(BaseModel):
    topic: str = Field(..., description="one of GET /topics")
    prompt: str = Field("", max_length=200, description="the start of the post")
    max_chars: int = Field(200, ge=1, le=MAX_CHARS)
    temperature: float = Field(0.8, ge=0.1, le=1.5)
    seed: int | None = Field(None, description="same seed + same input → same text")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    return {"ready": True, "version": VERSION, "load_seconds": LOAD_SECONDS}


@app.get("/topics")
def topics():
    return {"topics": TOPICS}


@app.post("/generate")
def generate(r: Request):
    if r.topic not in TOPICS:
        raise HTTPException(422, f"unknown topic {r.topic!r}; choose one of {TOPICS}")
    start = time.perf_counter()
    text = model.generate(tok, r.topic, r.prompt, r.max_chars, r.temperature, seed=r.seed)
    ms = round((time.perf_counter() - start) * 1000)
    log.info("generate topic=%s prompt_len=%d max_chars=%d ms=%d", r.topic, len(r.prompt), r.max_chars, ms)
    return {"topic": r.topic, "prompt": r.prompt, "text": text, "version": VERSION, "pod": POD, "ms": ms}
