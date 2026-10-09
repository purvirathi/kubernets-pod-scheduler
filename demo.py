from predict_node import recommend_node

pod = {
    "cpu_request": 0.5,
    "memory_request_gb": 1.0,
}

nodes = [
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

result = recommend_node(pod, nodes)

print("\nRecommended Node:", result["recommended_node"])
print("\nNode ranking:")
for c in result["candidates"]:
    print(
        f'{c["node_id"]}: feasible={c["feasible"]}, '
        f'probability={c["recommendation_probability"]:.4f}'
    )
