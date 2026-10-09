from k8s_model_adapter import get_node_features
from predict_node import recommend_node


def run_live_scheduler():
    print("\n" + "=" * 75)
    print("             LIVE AI KUBERNETES SCHEDULER")
    print("=" * 75)

    # Example Pod request
    pod = {
        "cpu_request": 0.5,
        "memory_request_gb": 0.5,
    }

    print("\nPod Request")
    print("-" * 75)
    print(f"CPU Request    : {pod['cpu_request']} cores")
    print(f"Memory Request : {pod['memory_request_gb']} GiB")

    # Get REAL Kubernetes node information
    nodes = get_node_features()

    if not nodes:
        print("\nNo Kubernetes nodes available.")
        return

    print("\nLive Kubernetes Nodes")
    print("-" * 75)

    for node in nodes:
        print(
            f"{node['node_id']:25}"
            f" CPU: {node['cpu_utilization_pct']:6.2f}%"
            f" | Memory: {node['memory_utilization_pct']:6.2f}%"
            f" | Pods: {node['running_pods']}"
        )

    # Send live data to Member 1's AI model
    result = recommend_node(pod, nodes)

    print("\n" + "=" * 75)
    print("                 AI SCHEDULING DECISION")
    print("=" * 75)

    print(f"\nRecommended Node : {result['recommended_node']}")
    print(f"Message          : {result['message']}")

    print("\nNode Ranking")
    print("-" * 75)

    for candidate in result["candidates"]:
        print(
            f"{candidate['node_id']:25}"
            f" | Feasible: {str(candidate['feasible']):5}"
            f" | AI Score: {candidate['recommendation_probability']:.4f}"
        )

    print("=" * 75)


if __name__ == "__main__":
    run_live_scheduler()
    