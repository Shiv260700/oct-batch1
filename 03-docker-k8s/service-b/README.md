# service-b: container volumes demo

A simple FastAPI service that appends each request to `/data/requests.log`.
Each line contains a UTC timestamp, HTTP method, path, and response status.
Endpoints: `GET /hello` and `GET /health`, both including hostname and port.

## Build and start

Run from `service-b`:

```sh
docker build -t service-b:latest .
docker run -d --name service-b -p 8081:8080 \
  --mount type=volume,source=service-b-data,target=/data service-b:latest
```

Docker creates the named volume if it does not exist. After startup, send requests
and inspect the log:

```sh
curl http://localhost:8081/hello
curl http://localhost:8081/health
docker exec service-b cat /data/requests.log
```

## Replace the container, keep the log

```sh
docker stop service-b
docker rm service-b
docker run -d --name service-b -p 8081:8080 \
  --mount type=volume,source=service-b-data,target=/data service-b:latest
docker exec service-b cat /data/requests.log
```

The previous log entries are still present. Send another request and inspect the
file again to see a new entry appended.

## Compare without a volume

```sh
docker run -d --name service-b-no-volume -p 8082:8080 service-b:latest
```

After startup:

```sh
curl http://localhost:8082/hello
docker exec service-b-no-volume cat /data/requests.log
docker stop service-b-no-volume
docker rm service-b-no-volume
docker run -d --name service-b-no-volume -p 8082:8080 service-b:latest
```

After startup, send another request and read the log:

```sh
curl http://localhost:8082/hello
docker exec service-b-no-volume cat /data/requests.log
```

Only the new request is present. A container's files survive stop/start, but are
lost when the container is removed unless persisted in a volume.

## Local development

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8081
```

Local logs go to `./data/requests.log`. Override `DATA_DIR` to change the directory.
