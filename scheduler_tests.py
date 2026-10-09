from scheduler import AIScheduler, print_scheduling_decision


scheduler = AIScheduler()


# ---------------------------------------------------------
# TEST 1: Normal scheduling
# ---------------------------------------------------------

pod_normal = {
    "cpu_request": 0.5,
    "memory_request_gb": 1.0,
}

nodes_normal = [
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

print("\n\nTEST 1: NORMAL SCHEDULING")

result = scheduler.schedule(pod_normal, nodes_normal)

print_scheduling_decision(result)


# ---------------------------------------------------------
# TEST 2: Highly utilized preferred node
# ---------------------------------------------------------

nodes_constrained = [
    {
        "node_id": "Node-1",
        "cpu_capacity_cores": 4.0,
        "memory_capacity_gb": 8.0,
        "cpu_utilization_pct": 98.0,
        "memory_utilization_pct": 95.0,
        "running_pods": 20,
    },
    {
        "node_id": "Node-2",
        "cpu_capacity_cores": 4.0,
        "memory_capacity_gb": 8.0,
        "cpu_utilization_pct": 40.0,
        "memory_utilization_pct": 35.0,
        "running_pods": 5,
    },
    {
        "node_id": "Node-3",
        "cpu_capacity_cores": 4.0,
        "memory_capacity_gb": 8.0,
        "cpu_utilization_pct": 55.0,
        "memory_utilization_pct": 45.0,
        "running_pods": 7,
    },
]

print("\n\nTEST 2: CONSTRAINED NODE")

result = scheduler.schedule(
    pod_normal,
    nodes_constrained
)

print_scheduling_decision(result)


# ---------------------------------------------------------
# TEST 3: No feasible node
# ---------------------------------------------------------

pod_too_large = {
    "cpu_request": 10.0,
    "memory_request_gb": 32.0,
}

print("\n\nTEST 3: NO FEASIBLE NODE")

result = scheduler.schedule(
    pod_too_large,
    nodes_normal
)

print_scheduling_decision(result)