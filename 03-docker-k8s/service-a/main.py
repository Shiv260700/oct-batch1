import json
import os
import socket
from urllib.error import URLError
from urllib.request import urlopen

from fastapi import FastAPI, HTTPException, Request

app = FastAPI(title="service-a")
SERVICE_B_URL = os.getenv("SERVICE_B_URL", "http://service-b:8080").rstrip("/")


@app.get("/hello")
def hello(request: Request):
    return {
        "message": "Hello, World!",
        "hostname": socket.gethostname(),
        "port": request.scope["server"][1],
    }


@app.get("/health")
def health(request: Request):
    return {
        "status": "ok",
        "hostname": socket.gethostname(),
        "port": request.scope["server"][1],
    }


@app.get("/call-service-b")
def call_service_b(request: Request):
    try:
        with urlopen(f"{SERVICE_B_URL}/hello", timeout=5) as response:
            service_b = json.load(response)
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Could not call service-b") from exc

    return {
        "hostname": socket.gethostname(),
        "port": request.scope["server"][1],
        "service_b": service_b,
    }
