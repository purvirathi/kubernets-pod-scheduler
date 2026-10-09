"""
Scheduling algorithms for the Kubernetes pod scheduler demo.

The project uses the same pod/node input shape for all algorithms so the UI can
compare First Come First Serve, Round Robin, and the ML-backed AI scheduler.
"""

from predict_node import recommend_node


ALGORITHMS = {
    "fcfs": {
        "id": "fcfs",
        "name": "First Come First Serve",
        "short_name": "FCFS",
        "description": "Scans nodes in order and chooses the first feasible node.",
    },
    "round_robin": {
        "id": "round_robin",
        "name": "Round Robin",
        "short_name": "RR",
        "description": "Rotates through schedulable nodes so work is spread evenly.",
    },
    "ai": {
        "id": "ai",
        "name": "AI Scheduler",
        "short_name": "AI",
        "description": "Uses the trained model to rank feasible nodes by placement score.",
    },
}

_round_robin_cursor = 0


def get_algorithms():
    return list(ALGORITHMS.values())


def _available_resources(node):
    cpu_capacity = float(node["cpu_capacity_cores"])
    mem_capacity = float(node["memory_capacity_gb"])
    cpu_available = max(0.0, cpu_capacity * (1 - float(node["cpu_utilization_pct"]) / 100))
    mem_available = max(0.0, mem_capacity * (1 - float(node["memory_utilization_pct"]) / 100))
    return cpu_available, mem_available


def _candidate_for_node(node, pod, score=0.0, reason=None):
    cpu_available, mem_available = _available_resources(node)
    schedulable = bool(node.get("schedulable", True))
    feasible = (
        schedulable
        and cpu_available >= float(pod["cpu_request"])
        and mem_available >= float(pod["memory_request_gb"])
    )

    if reason is None:
        if not schedulable:
            reason = "Node is cordoned or not schedulable"
        elif feasible:
            reason = "Enough CPU and memory are available"
        else:
            reason = "Insufficient CPU or memory for this pod"

    return {
        "node_id": node["node_id"],
        "feasible": feasible,
        "recommendation_probability": round(float(score), 4),
        "available_cpu_cores": round(cpu_available, 2),
        "available_memory_gb": round(mem_available, 2),
        "running_pods": int(node.get("running_pods", 0)),
        "reason": reason,
    }


def _first_come_first_serve(pod, nodes):
    candidates = []
    selected = None

    for index, node in enumerate(nodes):
        candidate = _candidate_for_node(node, pod, score=max(0.0, 1.0 - index * 0.1))
        candidates.append(candidate)
        if selected is None and candidate["feasible"]:
            selected = candidate["node_id"]
            candidate["reason"] = "First feasible node in cluster order"

    return {
        "recommended_node": selected,
        "message": "FCFS selected the first feasible node." if selected else "No feasible node found by FCFS.",
        "candidates": candidates,
    }


def _round_robin(pod, nodes):
    global _round_robin_cursor

    candidates = [_candidate_for_node(node, pod, score=0.0) for node in nodes]
    if not candidates:
        return {"recommended_node": None, "message": "No nodes available.", "candidates": []}

    node_count = len(nodes)
    selected = None
    start = _round_robin_cursor % node_count

    for offset in range(node_count):
        idx = (start + offset) % node_count
        if candidates[idx]["feasible"]:
            selected = candidates[idx]["node_id"]
            candidates[idx]["recommendation_probability"] = 1.0
            candidates[idx]["reason"] = "Next feasible node in the Round Robin cycle"
            _round_robin_cursor = (idx + 1) % node_count
            break

    for offset in range(node_count):
        idx = (start + offset) % node_count
        candidates[idx]["round_robin_order"] = offset + 1
        if selected and candidates[idx]["node_id"] != selected and candidates[idx]["feasible"]:
            candidates[idx]["recommendation_probability"] = round(max(0.1, 0.9 - offset * 0.1), 4)

    return {
        "recommended_node": selected,
        "message": "Round Robin selected the next feasible node." if selected else "No feasible node found by Round Robin.",
        "candidates": candidates,
    }


def _ai_scheduler(pod, nodes):
    try:
        result = recommend_node(pod, nodes)
    except Exception as exc:
        candidates = []
        for node in nodes:
            cpu_available, mem_available = _available_resources(node)
            candidate = _candidate_for_node(node, pod)
            if candidate["feasible"]:
                cpu_headroom = cpu_available / max(float(node["cpu_capacity_cores"]), 0.1)
                mem_headroom = mem_available / max(float(node["memory_capacity_gb"]), 0.1)
                balance_bonus = 1 - abs(float(node["cpu_utilization_pct"]) - float(node["memory_utilization_pct"])) / 100
                candidate["recommendation_probability"] = round(
                    max(0.05, min(0.99, (cpu_headroom + mem_headroom + balance_bonus) / 3)),
                    4,
                )
                candidate["reason"] = f"Heuristic AI fallback because ML model could not run: {exc}"
            candidates.append(candidate)

        feasible_candidates = [candidate for candidate in candidates if candidate["feasible"]]
        selected = None
        if feasible_candidates:
            selected = max(feasible_candidates, key=lambda item: item["recommendation_probability"])["node_id"]

        return {
            "recommended_node": selected,
            "message": "AI fallback ranking used because the saved ML model could not run on this machine.",
            "candidates": sorted(candidates, key=lambda item: item["recommendation_probability"], reverse=True),
        }

    candidates_by_node = {
        c["node_id"]: c
        for c in result.get("candidates", [])
    }
    candidates = []

    for node in nodes:
        ml_candidate = candidates_by_node.get(node["node_id"], {})
        candidate = _candidate_for_node(
            node,
            pod,
            score=ml_candidate.get("recommendation_probability", 0.0),
            reason="Ranked by trained AI model" if ml_candidate.get("feasible") else None,
        )
        candidate["feasible"] = bool(ml_candidate.get("feasible", candidate["feasible"]))
        candidates.append(candidate)

    candidates.sort(key=lambda item: item["recommendation_probability"], reverse=True)

    return {
        "recommended_node": result["recommended_node"],
        "message": result["message"],
        "candidates": candidates,
    }


def schedule_with_algorithm(algorithm, pod, nodes):
    algorithm = algorithm if algorithm in ALGORITHMS else "ai"

    if algorithm == "fcfs":
        result = _first_come_first_serve(pod, nodes)
    elif algorithm == "round_robin":
        result = _round_robin(pod, nodes)
    else:
        result = _ai_scheduler(pod, nodes)

    result["algorithm"] = ALGORITHMS[algorithm]
    return result
