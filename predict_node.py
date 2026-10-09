"""
predict_node.py
AI/ML recommendation module for the Kubernetes Pod Scheduler project.
"""

from pathlib import Path
import joblib
import pandas as pd

MODEL_PATH = Path(__file__).parent / "scheduler_model.joblib"
bundle = joblib.load(MODEL_PATH)
MODEL = bundle["model"]
FEATURE_COLUMNS = bundle["feature_columns"]


def _build_candidate_features(pod, node):
    cpu_request = float(pod["cpu_request"])
    mem_request = float(pod["memory_request_gb"])

    cpu_capacity = float(node["cpu_capacity_cores"])
    mem_capacity = float(node["memory_capacity_gb"])
    cpu_util = float(node["cpu_utilization_pct"])
    mem_util = float(node["memory_utilization_pct"])
    running_pods = int(node.get("running_pods", 0))

    available_cpu = max(0.0, cpu_capacity * (1 - cpu_util / 100))
    available_mem = max(0.0, mem_capacity * (1 - mem_util / 100))

    feasible = (
        available_cpu >= cpu_request
        and available_mem >= mem_request
    )

    post_cpu_util = (
        (cpu_capacity - available_cpu + cpu_request) / cpu_capacity
    ) * 100

    post_mem_util = (
        (mem_capacity - available_mem + mem_request) / mem_capacity
    ) * 100

    cpu_headroom_ratio = max(
        0.0, (available_cpu - cpu_request) / cpu_capacity
    )
    mem_headroom_ratio = max(
        0.0, (available_mem - mem_request) / mem_capacity
    )

    return {
        "pod_cpu_request": cpu_request,
        "pod_memory_request_gb": mem_request,
        "node_cpu_capacity_cores": cpu_capacity,
        "node_memory_capacity_gb": mem_capacity,
        "cpu_utilization_pct": cpu_util,
        "memory_utilization_pct": mem_util,
        "available_cpu_cores": available_cpu,
        "available_memory_gb": available_mem,
        "running_pods": running_pods,
        "post_cpu_utilization_pct": post_cpu_util,
        "post_memory_utilization_pct": post_mem_util,
        "cpu_headroom_ratio": cpu_headroom_ratio,
        "memory_headroom_ratio": mem_headroom_ratio,
        "feasible": int(feasible),
    }


def recommend_node(pod, nodes):
    """
    Recommend one feasible node.

    Returns a dictionary containing:
      - recommended_node
      - candidate probability/ranking information
    """
    if not nodes:
        raise ValueError("nodes list cannot be empty")

    candidates = []

    for node in nodes:
        features = _build_candidate_features(pod, node)
         # Safety rule 1:
    # Never recommend a node that Kubernetes marks unschedulable.
        if not node.get("schedulable", True):
            candidates.append({
                "node_id": node["node_id"],
                "feasible": False,
                "recommendation_probability": 0.0,
            })
            continue

    # Safety rule 2:
    # Never recommend a node that cannot satisfy resource requests.
        if features["feasible"] == 0:
            candidates.append({
                "node_id": node["node_id"],
                "feasible": False,
                "recommendation_probability": 0.0,
            })
            continue

        X = pd.DataFrame([features])[FEATURE_COLUMNS]
        probability = float(MODEL.predict_proba(X)[0][1])

        candidates.append({
            "node_id": node["node_id"],
            "feasible": True,
            "recommendation_probability": probability,
        })
    

    feasible_candidates = [c for c in candidates if c["feasible"]]

    if not feasible_candidates:
        return {
            "recommended_node": None,
            "message": "No node has enough available CPU and memory.",
            "candidates": candidates,
        }

    best = max(
        feasible_candidates,
        key=lambda c: c["recommendation_probability"]
    )

    return {
        "recommended_node": best["node_id"],
        "message": "ML model recommendation",
        "candidates": sorted(
            candidates,
            key=lambda c: c["recommendation_probability"],
            reverse=True
        )
    }


if __name__ == "__main__":
    sample_pod = {"cpu_request": 0.5, "memory_request_gb": 1.0}

    sample_nodes = [
        {
            "node_id": "Node-1",
            "cpu_capacity_cores": 4.0,
            "memory_capacity_gb": 8.0,
            "cpu_utilization_pct": 80.0,
            "memory_utilization_pct": 70.0,
            "running_pods": 10,
        },
        {
            "node_id": "Node-2",
            "cpu_capacity_cores": 4.0,
            "memory_capacity_gb": 8.0,
            "cpu_utilization_pct": 35.0,
            "memory_utilization_pct": 40.0,
            "running_pods": 5,
        },
        {
            "node_id": "Node-3",
            "cpu_capacity_cores": 4.0,
            "memory_capacity_gb": 8.0,
            "cpu_utilization_pct": 60.0,
            "memory_utilization_pct": 45.0,
            "running_pods": 7,
        },
    ]

    result = recommend_node(sample_pod, sample_nodes)
    print("Recommended Node:", result["recommended_node"])
    print("\nCandidate scores:")
    for item in result["candidates"]:
        print(item)
