from kubernetes import client, config
from k8s_model_adapter import get_node_features
from predict_node import recommend_node


SCHEDULER_NAME = "ai-scheduler"


def get_pending_pods(core_api):
    """
    Find Pods that are waiting for our custom scheduler.
    """
    pods = core_api.list_pod_for_all_namespaces(
        field_selector="status.phase=Pending"
    ).items

    pending = []

    for pod in pods:
        scheduler_name = pod.spec.scheduler_name

        if scheduler_name == SCHEDULER_NAME:
            pending.append(pod)

    return pending

def bind_pod(core_api, pod, node_name):
    """
    Bind a Pod to the selected Kubernetes node.
    """

    binding = {
        "apiVersion": "v1",
        "kind": "Binding",
        "metadata": {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
        },
        "target": {
            "apiVersion": "v1",
            "kind": "Node",
            "name": node_name,
        },
    }

    core_api.api_client.call_api(
    f"/api/v1/namespaces/{pod.metadata.namespace}/pods/"
    f"{pod.metadata.name}/binding",
    "POST",
    body=binding,
    response_types_map={},
    auth_settings=["BearerToken"],
    _preload_content=False,
)
def schedule_pod(core_api, pod):
    """
    Use the AI model to select a node and bind the Pod.
    """

    containers = pod.spec.containers

    cpu_request = 0.5
    memory_request_gb = 0.5

    if containers:
        requests = containers[0].resources.requests or {}

        if "cpu" in requests:
            cpu_value = str(requests["cpu"])

            if cpu_value.endswith("m"):
                cpu_request = float(cpu_value[:-1]) / 1000
            else:
                cpu_request = float(cpu_value)

        if "memory" in requests:
            memory_value = str(requests["memory"])

            if memory_value.endswith("Mi"):
                memory_request_gb = float(memory_value[:-2]) / 1024
            elif memory_value.endswith("Gi"):
                memory_request_gb = float(memory_value[:-2])

    pod_request = {
        "cpu_request": cpu_request,
        "memory_request_gb": memory_request_gb,
    }

    nodes = get_node_features()

    result = recommend_node(pod_request, nodes)

    selected_node = result["recommended_node"]

    print("\n" + "=" * 75)
    print("                 AI POD SCHEDULER")
    print("=" * 75)

    print(f"\nPod              : {pod.metadata.name}")
    print(f"CPU Request      : {cpu_request} cores")
    print(f"Memory Request   : {memory_request_gb:.2f} GiB")

    print("\nAI Decision")
    print("-" * 75)

    if selected_node is None:
        print("No suitable node found.")
        return

    print(f"Selected Node    : {selected_node}")

    print("\nNode Ranking")
    print("-" * 75)

    for candidate in result["candidates"]:
        print(
            f"{candidate['node_id']:25}"
            f" | Feasible: {str(candidate['feasible']):5}"
            f" | AI Score: {candidate['recommendation_probability']:.4f}"
        )

    # Actually bind the Pod to the selected node
    bind_pod(core_api, pod, selected_node)

    print("\nPod successfully bound to Kubernetes node.")
    print("=" * 75)


def main():
    config.load_kube_config()

    core_api = client.CoreV1Api()

    print("=" * 75)
    print("              AI KUBERNETES SCHEDULER")
    print("=" * 75)

    pending_pods = get_pending_pods(core_api)

    if not pending_pods:
        print("\nNo pending Pods found for ai-scheduler.")
        return

    print(f"\nPending Pods found: {len(pending_pods)}")

    for pod in pending_pods:
        schedule_pod(core_api, pod)


if __name__ == "__main__":
    main()
