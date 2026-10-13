import os
import socket
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request

app = FastAPI(title="service-b")
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))


@app.middleware("http")
async def log_request(request: Request, call_next):
    response = await call_next(request)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with (DATA_DIR / "requests.log").open("a", encoding="utf-8") as log:
        log.write(
            f"{datetime.now(timezone.utc).isoformat()} "
            f"{request.method} {request.url.path} {response.status_code}\n"
        )
    return response


def server_info(request: Request):
    return {"hostname": socket.gethostname(), "port": request.scope["server"][1]}


@app.get("/hello")
def hello(request: Request):
    return {"message": "Hello from service-b!", **server_info(request)}


@app.get("/health")
def health(request: Request):
    return {"status": "ok", **server_info(request)}
