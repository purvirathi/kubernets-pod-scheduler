from predict_node import recommend_node


class AIScheduler:
    """
    Kubernetes-inspired AI scheduler.

    Scheduling pipeline:
    1. Receive pod requirements and node states.
    2. Apply feasibility constraints through the AI module.
    3. Rank feasible nodes using the ML model.
    4. Return the scheduling decision.
    """

    def __init__(self):
        self.scheduler_name = "AI Pod Scheduler"

    def schedule(self, pod, nodes):
        """
        Schedule a pod onto the most suitable node.

        Parameters:
            pod: dictionary containing pod resource requirements
            nodes: list of dictionaries containing node information

        Returns:
            Dictionary containing the scheduling decision.
        """

        if not pod:
            raise ValueError("Pod information cannot be empty.")

        if not nodes:
            raise ValueError("Node list cannot be empty.")

        # Delegate node evaluation to Member 1's ML scheduler.
        result = recommend_node(pod, nodes)

        # No feasible node exists.
        if result["recommended_node"] is None:
            return {
                "status": "UNSCHEDULED",
                "pod": pod,
                "selected_node": None,
                "message": result["message"],
                "candidates": result["candidates"],
            }

        # Successful scheduling decision.
        selected_node = result["recommended_node"]

        return {
            "status": "SCHEDULED",
            "pod": pod,
            "selected_node": selected_node,
            "message": result["message"],
            "candidates": result["candidates"],
        }


def print_scheduling_decision(result):
    """
    Display the scheduler decision in a clean format.
    """

    print("\n" + "=" * 60)
    print("             AI KUBERNETES SCHEDULER")
    print("=" * 60)

    print(f"\nStatus        : {result['status']}")
    print(f"Selected Node : {result['selected_node']}")

    print(f"\nMessage       : {result['message']}")

    print("\nCandidate Node Ranking")
    print("-" * 60)

    for candidate in result["candidates"]:
        print(
            f"{candidate['node_id']:10}"
            f" | Feasible: {str(candidate['feasible']):5}"
            f" | AI Score: "
            f"{candidate['recommendation_probability']:.4f}"
        )

    print("=" * 60)


if __name__ == "__main__":

    # Example pod that needs to be scheduled.
    pod = {
        "cpu_request": 0.5,
        "memory_request_gb": 1.0,
    }

    # Simulated Kubernetes node state.
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

    scheduler = AIScheduler()

    result = scheduler.schedule(pod, nodes)

    print_scheduling_decision(result)