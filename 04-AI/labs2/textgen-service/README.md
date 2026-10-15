# textgen-api · the text generator as a Docker image

Lab 5's small GPT behind a web API: send a topic and the start of a post, get the continuation.

## Images
| Tag | For | Size |
|---|---|---|
| `textgen-api:v1` | arm64 (Apple silicon, ARM servers) | ≈ 1.3 GB |
| `textgen-api:v1-amd64` | amd64 (most cloud / on-prem Kubernetes nodes) | ≈ 1.3 GB |

Check your nodes: `kubectl get nodes -o jsonpath='{.items[*].status.nodeInfo.architecture}'`

## Get the image into your cluster
```bash
# a registry
docker tag textgen-api:v1-amd64 <registry>/textgen-api:v1
docker push <registry>/textgen-api:v1
# or kind
kind load docker-image textgen-api:v1 --name <cluster>
# or a file
docker save textgen-api:v1-amd64 | gzip > textgen-api-v1-amd64.tar.gz
```

## API (port 8000)
| Call | Purpose |
|---|---|
| `GET /health` | liveness: the process is up |
| `GET /ready` | readiness: the model is loaded (≈ 1.4 s after start) |
| `GET /topics` | `graphics, autos, hockey, med, space, guns` |
| `POST /generate` | generate text |

```bash
curl -s -X POST localhost:8000/generate -H 'content-type: application/json' \
  -d '{"topic": "space", "prompt": "The shuttle", "max_chars": 200, "temperature": 0.8, "seed": 1}'
```
- `topic` (required) · `prompt` ≤ 200 chars · `max_chars` 1–500 (default 200) · `temperature` 0.1–1.5 (default 0.8) · `seed` optional: same seed + same input → same text
- Bad input → **422** with the reason
- Reply: `topic, prompt, text, version, pod, ms`

## Settings (environment variables)
| Variable | Default | Meaning |
|---|---|---|
| `MODEL_VERSION` | `v1` | returned in every reply; change it to roll out a new version |
| `TORCH_THREADS` | `1` | fastest for this small model |
| `MAX_CHARS_LIMIT` | `500` | upper bound for `max_chars` |

## Measured (laptop, one container)
- Ready 1.4 s after start · memory ≈ 250 MiB
- ≈ 2 s for 200 characters with 1 thread (3.9 s with 4) · roughly linear in `max_chars`
- One request uses one CPU core: scale with replicas, not threads
- Runs as non-root (uid 10001); Docker `HEALTHCHECK` built in

## Kubernetes
- `k8s-example.yaml`: a reference Deployment + Service (2 replicas, probes on `/ready` and `/health`, 5 s preStop, 1 CPU / 384 Mi request)

## Rebuild after retraining
```bash
# from labs2/, after running 05-text-generation.ipynb
docker build -f textgen-service/Dockerfile -t textgen-api:v2 .
docker buildx build --platform linux/amd64 -f textgen-service/Dockerfile -t textgen-api:v2-amd64 --load .
```
