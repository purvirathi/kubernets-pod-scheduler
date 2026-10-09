from pathlib import Path
import random
import numpy as np
import pandas as pd

BASE = Path(__file__).parent
OUTPUT = BASE / "scheduler_dataset.csv"

N_SCENARIOS = 4000
random.seed(42)
np.random.seed(42)

rows = []

for scenario_id in range(1, N_SCENARIOS + 1):
    pod_cpu = round(np.random.uniform(0.1, 1.5), 2)
    pod_mem = round(np.random.uniform(0.25, 3.0), 2)
    candidates = []

    for node_num in range(1, 4):
        cpu_capacity = random.choice([2.0, 4.0, 8.0])
        mem_capacity = random.choice([4.0, 8.0, 16.0])
        cpu_util = np.random.uniform(15, 85)
        mem_util = np.random.uniform(15, 85)
        available_cpu = max(0.0, cpu_capacity * (1 - cpu_util / 100))
        available_mem = max(0.0, mem_capacity * (1 - mem_util / 100))
        running_pods = int(np.random.randint(2, 16))

        feasible = available_cpu >= pod_cpu and available_mem >= pod_mem
        post_cpu_util = ((cpu_capacity - available_cpu + pod_cpu) / cpu_capacity) * 100
        post_mem_util = ((mem_capacity - available_mem + pod_mem) / mem_capacity) * 100
        cpu_headroom_ratio = max(0.0, (available_cpu - pod_cpu) / cpu_capacity)
        memory_headroom_ratio = max(0.0, (available_mem - pod_mem) / mem_capacity)

        if feasible:
            score = (
                0.50 * max(0.0, 1 - post_cpu_util / 100)
                + 0.35 * max(0.0, 1 - post_mem_util / 100)
                + 0.10 * cpu_headroom_ratio
                + 0.05 * (1 - min(running_pods / 20.0, 1.0))
            )
        else:
            score = -1.0

        candidates.append({
            "scenario_id": scenario_id,
            "node_id": f"Node-{node_num}",
            "pod_cpu_request": pod_cpu,
            "pod_memory_request_gb": pod_mem,
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
            "memory_headroom_ratio": memory_headroom_ratio,
            "feasible": int(feasible),
            "_score": score,
        })

    feasible_nodes = [c for c in candidates if c["feasible"] == 1]

    if not feasible_nodes:
        c = min(candidates, key=lambda x: x["cpu_utilization_pct"] + x["memory_utilization_pct"])
        c["node_cpu_capacity_cores"] = max(4.0, c["node_cpu_capacity_cores"], pod_cpu * 2)
        c["node_memory_capacity_gb"] = max(8.0, c["node_memory_capacity_gb"], pod_mem * 2)
        c["available_cpu_cores"] = c["node_cpu_capacity_cores"] * (1 - c["cpu_utilization_pct"] / 100)
        c["available_memory_gb"] = c["node_memory_capacity_gb"] * (1 - c["memory_utilization_pct"] / 100)

        if c["available_cpu_cores"] < pod_cpu:
            c["cpu_utilization_pct"] = 20.0
            c["available_cpu_cores"] = c["node_cpu_capacity_cores"] * 0.80
        if c["available_memory_gb"] < pod_mem:
            c["memory_utilization_pct"] = 20.0
            c["available_memory_gb"] = c["node_memory_capacity_gb"] * 0.80

        c["post_cpu_utilization_pct"] = (
            (c["node_cpu_capacity_cores"] - c["available_cpu_cores"] + pod_cpu)
            / c["node_cpu_capacity_cores"]
        ) * 100
        c["post_memory_utilization_pct"] = (
            (c["node_memory_capacity_gb"] - c["available_memory_gb"] + pod_mem)
            / c["node_memory_capacity_gb"]
        ) * 100
        c["cpu_headroom_ratio"] = max(0.0, (c["available_cpu_cores"] - pod_cpu) / c["node_cpu_capacity_cores"])
        c["memory_headroom_ratio"] = max(0.0, (c["available_memory_gb"] - pod_mem) / c["node_memory_capacity_gb"])
        c["feasible"] = 1
        c["score"] = (
            0.50 * max(0.0, 1 - c["post_cpu_utilization_pct"] / 100)
            + 0.35 * max(0.0, 1 - c["post_memory_utilization_pct"] / 100)
            + 0.10 * c["cpu_headroom_ratio"]
            + 0.05 * (1 - min(c["running_pods"] / 20.0, 1.0))
        )
        c["_score"] = c["score"]
        del c["score"]
        feasible_nodes = [c for c in candidates if c["feasible"] == 1]

    winner = max(feasible_nodes, key=lambda x: x["_score"])["node_id"]

    for c in candidates:
        c["recommended"] = int(c["node_id"] == winner)
        del c["_score"]
        rows.append(c)

df = pd.DataFrame(rows)
df.to_csv(OUTPUT, index=False)
print(f"Created {len(df)} rows at {OUTPUT}")
