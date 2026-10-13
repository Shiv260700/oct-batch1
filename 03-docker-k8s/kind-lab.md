# Lab: Kubernetes with kind on macOS Docker Desktop

## 1. Prerequisites

Start Docker Desktop and wait for its engine to be ready.

```sh
docker info
uname -m
```

Apple Silicon Macs use `arm64`; Intel Macs use `amd64` binaries. Download
`darwin` binaries for macOS, even though Docker runs Linux containers.

## 2. Install kubectl and kind

Download the macOS binaries directly using `curl`:

```sh
ARCH=$(uname -m)
[ "$ARCH" = "x86_64" ] && ARCH=amd64

KUBECTL_VERSION=$(curl -fsSL https://dl.k8s.io/release/stable.txt)
curl -fLo kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/darwin/${ARCH}/kubectl"
curl -fLo kind "https://kind.sigs.k8s.io/dl/v0.33.0/kind-darwin-${ARCH}"
chmod +x kubectl kind
sudo mkdir -p /usr/local/bin
sudo mv kubectl kind /usr/local/bin/
```

Verify installation:

```sh
kubectl version --client
kind version
```

Use a kubectl version within one minor version of your Kubernetes cluster.

## 3. Review the cluster configuration

The accompanying `kind-cluster.yaml` defines one control-plane node and two workers:

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
```

## 4. Create the cluster yourself

Run from the project directory:

```sh
kind create cluster --name kind-cluster --config kind-cluster.yaml --wait 120s
kind get clusters
kubectl config use-context kind-kind-cluster
kubectl get nodes -o wide
kubectl cluster-info
docker ps
```

Each Kubernetes node appears as a Docker container. Expect all three nodes to
become `Ready`. If creation fails due to memory pressure, increase Docker Desktop's
resource allocation or remove a worker from the configuration.

## 5. Explore the cluster

```sh
kubectl get pods -A
kubectl get storageclass
kubectl api-resources
kubectl config get-contexts
kubectl create namespace demo
kubectl config set-context --current --namespace=demo
```

`api-resources` lists available resource types. `get pods -A` lists deployed pods
across all namespaces.

## 6. Load the demo service images

```sh
docker build -t service-a:lab ./service-a
docker build -t service-b:lab ./service-b
kind load docker-image service-a:lab service-b:lab --name kind-cluster
```

Loading an image does not deploy the application. Later, use these image tags
in Kubernetes manifests with `imagePullPolicy: IfNotPresent`.

## 7. Delete the lab cluster

```sh
kind delete cluster --name kind-cluster
kind get clusters
```

This removes the Kubernetes cluster and its node containers, including data
stored inside those nodes.

## References

- [kind quick start](https://kind.sigs.k8s.io/docs/user/quick-start/)
- [Install kubectl on macOS](https://kubernetes.io/docs/tasks/tools/install-kubectl-macos/)
