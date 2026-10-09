"""
backend_api.py
Flask API for the AI Kubernetes Pod Scheduler.

Supports two modes:
  1. Live mode  — reads real data from a Kubernetes cluster.
  2. Simulation — uses realistic synthetic data when no cluster is available.

The mode is selected automatically at startup.
"""

import random
import time
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

from scheduling_algorithms import get_algorithms, schedule_with_algorithm

# ---------------------------------------------------------------------------
# Try to import the Kubernetes adapter.  If it fails (no cluster / no
# kubeconfig) we fall back to simulation mode automatically.
# ---------------------------------------------------------------------------

USE_LIVE_K8S = False

try:
    from k8s_model_adapter import get_node_features as _live_get_node_features

    # Quick smoke-test: actually call it once so we crash early if the
    # cluster is unreachable rather than crashing on the first request.
    _live_get_node_features()
    USE_LIVE_K8S = True
    print("[OK] Connected to live Kubernetes cluster.")

except Exception as exc:
    print(f"[!] Kubernetes not available ({exc}). Using simulation mode.")

# ---------------------------------------------------------------------------
# Simulation helpers
# ---------------------------------------------------------------------------

_SIM_NODES = [
    {
        "node_id": "node-worker-01",
        "cpu_capacity_cores": 4.0,
        "memory_capacity_gb": 8.0,
        "cpu_utilization_pct": 42.0,
        "memory_utilization_pct": 58.0,
        "running_pods": 6,
        "schedulable": True,
    },
    {
        "node_id": "node-worker-02",
        "cpu_capacity_cores": 8.0,
        "memory_capacity_gb": 16.0,
        "cpu_utilization_pct": 31.0,
        "memory_utilization_pct": 46.0,
        "running_pods": 4,
        "schedulable": True,
    },
    {
        "node_id": "node-worker-03",
        "cpu_capacity_cores": 4.0,
        "memory_capacity_gb": 8.0,
        "cpu_utilization_pct": 55.0,
        "memory_utilization_pct": 67.0,
        "running_pods": 8,
        "schedulable": True,
    },
]

_SIM_PODS = [
    {"name": "coredns-5dd5756b68-abc12", "namespace": "kube-system", "node": "node-worker-01", "status": "Running", "cpu_request": 0.1, "memory_request_gb": 0.07, "containers": [{"name": "coredns", "image": "registry.k8s.io/coredns/coredns", "role": "dns"}]},
    {"name": "kube-proxy-xyz42", "namespace": "kube-system", "node": "node-worker-02", "status": "Running", "cpu_request": 0.0, "memory_request_gb": 0.0, "containers": [{"name": "kube-proxy", "image": "registry.k8s.io/kube-proxy", "role": "network"}]},
    {"name": "storefront-frontend-7fc8b9c4-p1q2r", "namespace": "default", "node": "node-worker-01", "status": "Running", "cpu_request": 0.25, "memory_request_gb": 0.128, "containers": [{"name": "frontend", "image": "demo/frontend:v1", "role": "ui"}]},
    {"name": "orders-api-7fc8b9c4-s3t4u", "namespace": "default", "node": "node-worker-02", "status": "Running", "cpu_request": 0.35, "memory_request_gb": 0.256, "containers": [{"name": "api", "image": "demo/orders-api:v1", "role": "service"}]},
    {"name": "redis-cache-0", "namespace": "default", "node": "node-worker-03", "status": "Running", "cpu_request": 0.5, "memory_request_gb": 0.256, "containers": [{"name": "redis", "image": "redis:7", "role": "cache"}]},
    {"name": "analytics-worker-6c9d7e8f-v5w6x", "namespace": "default", "node": "node-worker-02", "status": "Running", "cpu_request": 0.5, "memory_request_gb": 0.512, "containers": [{"name": "worker", "image": "demo/analytics-worker:v1", "role": "processor"}]},
]

CONTAINER_PROFILES = {
    "web-stack": [
        {"name": "web", "image": "nginx:1.27-alpine", "role": "HTTP frontend", "cpu_request": 0.2, "memory_request_gb": 0.2},
        {"name": "api", "image": "busybox:1.36", "role": "Business API", "cpu_request": 0.2, "memory_request_gb": 0.2},
        {"name": "sidecar", "image": "busybox:1.36", "role": "Logging sidecar", "cpu_request": 0.1, "memory_request_gb": 0.1},
    ],
    "data-pipeline": [
        {"name": "collector", "image": "busybox:1.36", "role": "Input collector", "cpu_request": 0.3, "memory_request_gb": 0.25},
        {"name": "processor", "image": "busybox:1.36", "role": "Batch processor", "cpu_request": 0.4, "memory_request_gb": 0.5},
        {"name": "exporter", "image": "busybox:1.36", "role": "Result exporter", "cpu_request": 0.2, "memory_request_gb": 0.25},
    ],
    "ml-service": [
        {"name": "inference", "image": "python:3.12-alpine", "role": "Prediction server", "cpu_request": 0.6, "memory_request_gb": 0.8},
        {"name": "model-cache", "image": "busybox:1.36", "role": "Model cache", "cpu_request": 0.2, "memory_request_gb": 0.4},
        {"name": "metrics", "image": "busybox:1.36", "role": "Metrics exporter", "cpu_request": 0.1, "memory_request_gb": 0.1},
    ],
}


def _containers_for_profile(profile_id):
    containers = CONTAINER_PROFILES.get(profile_id, CONTAINER_PROFILES["web-stack"])
    return [dict(container) for container in containers]


def _memory_gb_to_mi(memory_gb):
    return f"{max(1, int(float(memory_gb) * 1024))}Mi"


def _safe_k8s_name(name):
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in name)
    safe = "-".join(part for part in safe.split("-") if part)
    return (safe or f"pod-{int(time.time())}")[:63].strip("-")


def _create_live_pod(pod_name, node_name, containers, algorithm_id):
    from kubernetes import client, config

    config.load_kube_config()
    v1 = client.CoreV1Api()
    safe_name = _safe_k8s_name(pod_name)

    k8s_containers = []
    for container in containers:
        command = None
        args = None
        if "nginx" not in container["image"]:
            command = ["sh", "-c"]
            args = ["while true; do sleep 3600; done"]

        k8s_containers.append(client.V1Container(
            name=_safe_k8s_name(container["name"]),
            image=container["image"],
            command=command,
            args=args,
            resources=client.V1ResourceRequirements(
                requests={
                    "cpu": str(container.get("cpu_request", 0.1)),
                    "memory": _memory_gb_to_mi(container.get("memory_request_gb", 0.1)),
                }
            ),
        ))

    body = client.V1Pod(
        metadata=client.V1ObjectMeta(
            name=safe_name,
            labels={
                "app": "scheduler-demo",
                "scheduled-by": algorithm_id,
            },
            annotations={
                "scheduler-demo/original-name": pod_name,
                "scheduler-demo/algorithm": algorithm_id,
            },
        ),
        spec=client.V1PodSpec(
            node_name=node_name,
            restart_policy="Always",
            containers=k8s_containers,
        ),
    )

    try:
        v1.create_namespaced_pod(namespace="default", body=body)
        return safe_name, None
    except client.exceptions.ApiException as exc:
        if exc.status == 409:
            unique_name = _safe_k8s_name(f"{safe_name}-{int(time.time())}")
            body.metadata.name = unique_name
            v1.create_namespaced_pod(namespace="default", body=body)
            return unique_name, None
        return None, str(exc)


def _get_sim_nodes():
    """Return simulation nodes with slight random jitter for realism."""
    result = []
    for node in _SIM_NODES:
        n = dict(node)
        n["cpu_utilization_pct"] = round(
            max(5, min(95, n["cpu_utilization_pct"] + random.uniform(-3, 3))), 1
        )
        n["memory_utilization_pct"] = round(
            max(5, min(95, n["memory_utilization_pct"] + random.uniform(-2, 2))), 1
        )
        result.append(n)
    return result


def _get_sim_pods():
    """Return simulated pod list."""
    return list(_SIM_PODS)


# ---------------------------------------------------------------------------
# Unified data-access functions
# ---------------------------------------------------------------------------


def get_nodes():
    if USE_LIVE_K8S:
        return _live_get_node_features()
    return _get_sim_nodes()


def get_pods():
    if USE_LIVE_K8S:
        # Live mode: fetch pods from K8s
        try:
            from kubernetes import client, config

            config.load_kube_config()
            v1 = client.CoreV1Api()
            items = v1.list_pod_for_all_namespaces().items
            pods = []
            for pod in items:
                cpu_req = 0.0
                mem_req = 0.0
                if pod.spec.containers:
                    for c in pod.spec.containers:
                        if c.resources and c.resources.requests:
                            cpu_val = c.resources.requests.get("cpu", "0")
                            mem_val = c.resources.requests.get("memory", "0")
                            from k8s_model_adapter import parse_cpu, parse_memory
                            cpu_req += parse_cpu(cpu_val)
                            mem_req += parse_memory(mem_val)
                pods.append({
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "node": pod.spec.node_name or "Pending",
                    "status": pod.status.phase,
                    "cpu_request": round(cpu_req, 3),
                    "memory_request_gb": round(mem_req, 3),
                    "containers": [
                        {
                            "name": c.name,
                            "image": c.image,
                            "role": "container",
                        }
                        for c in (pod.spec.containers or [])
                    ],
                })
            return pods
        except Exception:
            return []
    return _get_sim_pods()


# ---------------------------------------------------------------------------
# Scheduling history (in-memory)
# ---------------------------------------------------------------------------

scheduling_history = []


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__)
CORS(app)


@app.get("/")
def home():
    return jsonify({
        "message": "Kubernetes Scheduler API is running",
        "mode": "live" if USE_LIVE_K8S else "simulation",
        "algorithms": [item["id"] for item in get_algorithms()],
    })


@app.get("/api/algorithms")
def api_algorithms():
    return jsonify({
        "success": True,
        "algorithms": get_algorithms(),
        "container_profiles": [
            {
                "id": profile_id,
                "name": profile_id.replace("-", " ").title(),
                "containers": containers,
                "cpu_request": round(sum(c["cpu_request"] for c in containers), 2),
                "memory_request_gb": round(sum(c["memory_request_gb"] for c in containers), 2),
            }
            for profile_id, containers in CONTAINER_PROFILES.items()
        ],
    })


@app.get("/api/nodes")
def api_get_nodes():
    try:
        nodes = get_nodes()
        return jsonify({"success": True, "nodes": nodes})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.get("/api/pods")
def api_get_pods():
    try:
        pods = get_pods()
        return jsonify({"success": True, "pods": pods})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.get("/api/topology")
def api_topology():
    try:
        nodes = get_nodes()
        pods = get_pods()
        pods_by_node = {
            node["node_id"]: [pod for pod in pods if pod.get("node") == node["node_id"]]
            for node in nodes
        }
        return jsonify({
            "success": True,
            "topology": [
                {
                    "node": node,
                    "pods": pods_by_node.get(node["node_id"], []),
                    "pod_count": len(pods_by_node.get(node["node_id"], [])),
                    "container_count": sum(
                        len(pod.get("containers", []))
                        for pod in pods_by_node.get(node["node_id"], [])
                    ),
                }
                for node in nodes
            ],
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.get("/api/cluster-stats")
def api_cluster_stats():
    try:
        nodes = get_nodes()
        pods = get_pods()

        total_cpu_cap = sum(n["cpu_capacity_cores"] for n in nodes)
        total_mem_cap = sum(n["memory_capacity_gb"] for n in nodes)

        avg_cpu = (
            sum(n["cpu_utilization_pct"] for n in nodes) / len(nodes)
            if nodes else 0
        )
        avg_mem = (
            sum(n["memory_utilization_pct"] for n in nodes) / len(nodes)
            if nodes else 0
        )

        schedulable = sum(1 for n in nodes if n.get("schedulable", True))
        running_pods = sum(1 for p in pods if p.get("status") == "Running")
        total_containers = sum(len(p.get("containers", [])) for p in pods)
        algorithm_counts = {}
        for h in scheduling_history:
            name = h.get("algorithm", {}).get("short_name", "AI")
            algorithm_counts[name] = algorithm_counts.get(name, 0) + 1

        return jsonify({
            "success": True,
            "stats": {
                "total_nodes": len(nodes),
                "schedulable_nodes": schedulable,
                "total_pods": len(pods),
                "running_pods": running_pods,
                "total_containers": total_containers,
                "avg_cpu_pct": round(avg_cpu, 1),
                "avg_mem_pct": round(avg_mem, 1),
                "total_cpu_cores": round(total_cpu_cap, 1),
                "total_memory_gb": round(total_mem_cap, 1),
                "algorithm_counts": algorithm_counts,
            },
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.post("/api/schedule")
def schedule_pod():
    try:
        data = request.get_json(silent=True) or {}

        pod_name = data.get("pod_name", f"pod-{int(time.time())}")
        algorithm = data.get("algorithm", "ai")
        profile_id = data.get("container_profile", "web-stack")
        containers = data.get("containers") or _containers_for_profile(profile_id)
        cpu_req = float(data.get("cpu_request") or sum(c.get("cpu_request", 0) for c in containers) or 0.5)
        mem_req = float(data.get("memory_request_gb") or sum(c.get("memory_request_gb", 0) for c in containers) or 0.5)

        pod = {
            "cpu_request": cpu_req,
            "memory_request_gb": mem_req,
            "containers": containers,
        }

        nodes = get_nodes()

        if not nodes:
            return jsonify({
                "success": False,
                "error": "No Kubernetes nodes available",
            }), 503

        result = schedule_with_algorithm(algorithm, pod, nodes)

        # Build history entry
        entry = {
            "id": len(scheduling_history) + 1,
            "pod_name": pod_name,
            "algorithm": result["algorithm"],
            "cpu_request": cpu_req,
            "memory_request_gb": mem_req,
            "containers": containers,
            "recommended_node": result["recommended_node"],
            "message": result["message"],
            "candidates": result["candidates"],
            "status": "SCHEDULED" if result["recommended_node"] else "FAILED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        scheduling_history.insert(0, entry)

        # In simulation mode, if scheduled, add the pod to the simulated pod
        # list so that subsequent /api/pods calls reflect the new pod.
        if not USE_LIVE_K8S and result["recommended_node"]:
            _SIM_PODS.append({
                "name": pod_name,
                "namespace": "default",
                "node": result["recommended_node"],
                "status": "Running",
                "cpu_request": cpu_req,
                "memory_request_gb": mem_req,
                "containers": containers,
                "scheduled_by": result["algorithm"]["id"],
            })

            # Also update the node utilization to reflect the new pod
            for node in _SIM_NODES:
                if node["node_id"] == result["recommended_node"]:
                    node["running_pods"] += 1
                    cpu_cap = node["cpu_capacity_cores"]
                    mem_cap = node["memory_capacity_gb"]
                    node["cpu_utilization_pct"] = round(min(95, node["cpu_utilization_pct"] + (cpu_req / cpu_cap) * 100), 1)
                    node["memory_utilization_pct"] = round(min(95, node["memory_utilization_pct"] + (mem_req / mem_cap) * 100), 1)
                    break

        live_pod_name = None
        live_create_error = None
        if USE_LIVE_K8S and result["recommended_node"]:
            live_pod_name, live_create_error = _create_live_pod(
                pod_name,
                result["recommended_node"],
                containers,
                result["algorithm"]["id"],
            )
            if live_create_error:
                entry["message"] = f"{entry['message']} Pod creation failed: {live_create_error}"

        return jsonify({
            "success": True,
            "pod_name": pod_name,
            "live_pod_name": live_pod_name,
            "live_create_error": live_create_error,
            "pod": pod,
            "algorithm": result["algorithm"],
            "recommended_node": result["recommended_node"],
            "message": result["message"],
            "candidates": result["candidates"],
            "status": entry["status"],
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.get("/api/history")
def api_history():
    return jsonify({
        "success": True,
        "history": scheduling_history,
    })


if __name__ == "__main__":
    print(f"\n  Mode: {'LIVE Kubernetes' if USE_LIVE_K8S else 'SIMULATION'}")
    print("  Starting on http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
