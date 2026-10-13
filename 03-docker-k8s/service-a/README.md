# service-a

A simple FastAPI application with hello and health endpoints.

## Run locally

```sh
cd service-a
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

## Endpoints

- `GET /hello` returns `{"message": "Hello, World!", "hostname": "your-hostname", "port": 8080}`.
- `GET /health` returns `{"status": "ok", "hostname": "your-hostname", "port": 8080}`.
- `GET /call-service-b` calls service-b's `/hello` and returns its response under `service_b` along with service-a's hostname and port. Returns 502 if the call fails.
- `hostname` is the machine or container hostname; `port` is the server port handling the request.
- Interactive API documentation: http://127.0.0.1:8080/docs

```sh
curl http://127.0.0.1:8080/hello
curl http://127.0.0.1:8080/health
```

## Custom bridge networking demo

### Using Docker Compose

From the project root:

```sh
docker compose up -d --build
docker compose ps
curl http://localhost:8080/call-service-b
curl http://localhost:8081/hello
docker compose exec service-b cat /data/requests.log
```

Compose builds both services, creates a custom bridge network, and mounts a named
volume at `/data` for service-b. Service-a waits for service-b's healthcheck and
calls it at `http://service-b:8080`. Healthcheck requests also appear in the log.
Stop any earlier containers occupying host ports 8080 or 8081 before starting.

To demonstrate persistence:

```sh
docker compose down
docker compose up -d
docker compose exec service-b cat /data/requests.log
```

The log survives `down` and `up`. `docker compose down -v` deletes the volume
and its stored logs. Compose creates its own project-scoped volume; it does not
reuse the `service-b-data` volume from the manual Docker commands below.

### Using Docker directly

Run these commands from the project root. If containers named `service-a` or
`service-b` already exist, stop and remove them before running replacements.

```sh
docker build -t service-a:latest ./service-a
docker build -t service-b:latest ./service-b
docker network create --driver bridge demo-net
docker run -d --name service-b --network demo-net \
  --mount type=volume,source=service-b-data,target=/data service-b:latest
docker run -d --name service-a --network demo-net -p 8080:8080 \
  -e SERVICE_B_URL=http://service-b:8080 service-a:latest
```

After both services start:

```sh
curl http://localhost:8080/call-service-b
docker exec service-b cat /data/requests.log
```

The response contains both containers' hostnames. The log in service-b contains
`GET /hello 200`, showing the request arrived from service-a.

Traffic flows from your host to service-a on published port 8080, then from
service-a to `http://service-b:8080/hello` over `demo-net`. Docker's custom bridge
resolves the container name `service-b`; service-b does not need a published host
port for this communication. See [Docker bridge networking](https://docs.docker.com/engine/network/drivers/bridge/).

Inside service-a, `localhost` refers to service-a itself. Use the other container's
name and its internal port to reach service-b.

For local development outside Docker, start service-b on port 8081 yourself and
start service-a with:

```sh
SERVICE_B_URL=http://127.0.0.1:8081 uvicorn main:app --reload --port 8080
```
