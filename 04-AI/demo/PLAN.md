# Demo plan: production log analyst

**v1 = chatbot over Apache + Java server logs · v2 = the same chatbot with RAG · served with FastAPI.**
No Claude, no ChatGPT, no Ollama: a small open-source model runs locally with Hugging Face `transformers`.

## Decisions

| Item | Choice |
|---|---|
| Logs | Synthetic **Apache + Java server logs**: Apache httpd (access_log, error_log) in front of a Java Spring Boot app on Tomcat (application log with stack traces, catalina.out with OutOfMemoryError / restarts), 3 days, planted incidents with a known answer key |
| Language model | `Qwen/Qwen2.5-0.5B-Instruct` (Apache-2.0, ~1 GB, one-time download ≈ 30 min here). Setting `MODEL_ID` switches to `Qwen2.5-1.5B-Instruct` (~3 GB) for better answers |
| Search (RAG) | `all-MiniLM-L6-v2` (already cached) + plain numpy cosine similarity (no vector database needed at this size) |
| Serving | FastAPI + uvicorn, API endpoints only |
| Python | `~/ai/labs/.venv` (pandas, torch, transformers, sentence-transformers, fastapi, uvicorn, httpx already installed) |
| Design rule | Code finds the facts; the small model only phrases the answer and must cite its sources |

## The logs (what we generate)

Service `shop-app` (Java 17, Spring Boot on Tomcat, HikariCP pool to PostgreSQL) behind Apache httpd (`mod_proxy`), calling an external payment gateway.

| File | Example line |
|---|---|
| `apache/access_log` (combined format) | `10.0.3.21 - - [14/Oct/2026:09:15:02 +0000] "GET /api/orders/42 HTTP/1.1" 200 512 "-" "Mozilla/5.0" 35ms` |
| `apache/error_log` | `[Wed Oct 14 11:02:10.123 2026] [proxy_http:error] [pid 2211] (70007)The timeout specified has expired: AH01102: error reading status line from remote server 127.0.0.1:8080` |
| `app/application.log` (Spring Boot / logback) | `2026-10-14 09:15:02.140 ERROR 4512 --- [nio-8080-exec-7] c.shop.orders.OrderService : HikariPool-1 - Connection is not available, request timed out after 30000ms.` + Java stack trace |
| `tomcat/catalina.out` | `java.lang.OutOfMemoryError: Java heap space` · `INFO: Server startup in [5432] milliseconds` |
| `deploys.log` | `2026-10-15 14:00 deploy shop-app v1.4.2` · `2026-10-15 14:40 rollback to v1.4.1` |

**Planted incidents (the answer key, `incidents.json`):**

1. **DB connection pool exhausted:** HikariCP `Connection is not available, request timed out after 30000ms` → 500s and slow `/api/orders`.
2. **Memory leak:** heap grows → `java.lang.OutOfMemoryError: Java heap space` → Tomcat restart → Apache `502/503` and `AH01102` proxy errors.
3. **Slow payment gateway:** `java.net.SocketTimeoutException: Read timed out` on `/api/checkout` → response-time spike in the access log.
4. **Bad deploy v1.4.2:** `NullPointerException` in `UserMapper.toDto` → 500s on `/api/users` until the rollback.
5. **Login brute force:** `401` spike from one IP on `/api/login` (access log only).

Plus normal traffic and harmless noise (health checks, 404s for `favicon.ico`, bots, retries, GC info lines).

**Knowledge base for RAG (`kb/*.md`):** one runbook per incident type (HikariCP pool, Java heap/OOM, gateway timeouts, rollback, blocking an IP), the service architecture, and two past post-mortems.

## Folder

```
demo/
  PLAN.md, README.md, requirements.txt
  data/
    logs/        apache/access_log · apache/error_log · app/application.log · tomcat/catalina.out · deploys.log
    incidents.json   (answer key)
    kb/          runbooks, architecture, post-mortems
  logbot/        shared code used by the notebooks and the API
    parse.py     Apache combined + error_log, logback lines, multi-line Java stack traces → one table (time, source, level, endpoint, status, latency, ip, exception, message)
    tools.py     error counts, timeline, top errors, first/last occurrence, follow one request id
    llm.py       load the local model once; chat template; generate
    rag.py       chunk logs + kb, embed, search, build the prompt with sources
    prompts.py   system prompts (“answer only from the given logs; say ‘not in the logs’; cite sources”)
  index/         saved embeddings + chunk metadata
  app/main.py    FastAPI service
  00 … 06 notebooks
```

## Notebooks

| # | Notebook | What it shows | Check at the end |
|---|---|---|---|
| 00 | `00-make-data` | Generate 3 days of logs with the 5 planted incidents, the answer key and the runbooks | every planted incident appears in the logs at the right time |
| 01 | `01-read-logs` | Parse Apache and Java logs into one table (stack traces joined to their error line); requests per minute, 5xx timeline, top exceptions, link Apache 502s to Tomcat restarts | the timeline shows 5 spikes at the planted times |
| 02 | `02-local-model` | Download/load the model once; first answer; tokens per second; what it does with no logs (makes things up) | model loads offline from the cache |
| 03 | `03-v1-chatbot` | **v1:** chat with history; the prompt gets a short log summary + the latest errors (fits the context window) | answers “what is happening now?”; misses older incidents; invents details |
| 04 | `04-v2-rag` | **v2:** chunk logs (per file, 5-minute windows) + runbooks → MiniLM → top-k search (with a time/service filter) → answer with the exact log lines and the runbook fix, or “not in the logs” | each answer lists its sources |
| 05 | `05-evaluate` | 20 questions with known answers (root cause, first error time, affected endpoint, fix, “did X happen?” traps); v1 vs v2 side by side | v2 beats v1 on correct answers and made-up answers; response time shown |
| 06 | `06-fastapi` | Start the API from the notebook; call every endpoint with httpx; show JSON answers with sources | all endpoints return 200; v2 cites log lines |

## FastAPI endpoints

| Endpoint | Does |
|---|---|
| `GET /health` | process is alive |
| `GET /ready` | model and index are loaded |
| `POST /v1/chat` | `{session_id, message}` → answer (v1, keeps chat history per session) |
| `POST /v2/ask` | `{question, service?, since?, until?}` → `{answer, sources: [{file, line, text}], latency_ms}` |
| `POST /v2/ingest` | add a new log file → re-chunk and re-index |
| `GET /stats` | quick numbers: requests, error rate, top errors (no model needed) |

## What the demo proves (measured in notebook 05)

- v1 sounds fluent but only knows what fits in its summary; it misses older incidents and invents details.
- v2 finds the right log lines and the runbook fix, cites them, and says “not in the logs” when the answer isn’t there.
- Both run fully offline on a laptop and are served by FastAPI.
