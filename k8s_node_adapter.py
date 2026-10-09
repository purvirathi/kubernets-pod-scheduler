from kubernetes import client, config


def parse_cpu(cpu_value):
    """
    Convert Kubernetes CPU quantity to CPU cores.

    Examples:
        "4"     -> 4.0
        "500m"  -> 0.5
    """
    cpu_value = str(cpu_value)

    if cpu_value.endswith("m"):
        return float(cpu_value[:-1]) / 1000

    return float(cpu_value)


def parse_memory(memory_value):
    """
    Convert Kubernetes memory quantity to GiB.

    Kubernetes commonly reports memory using Ki, Mi or Gi.
    """
    memory_value = str(memory_value)

    if memory_value.endswith("Ki"):
        return float(memory_value[:-2]) / (1024 ** 2)

    if memory_value.endswith("Mi"):
        return float(memory_value[:-2]) / 1024

    if memory_value.endswith("Gi"):
        return float(memory_value[:-2])

    if memory_value.endswith("Ti"):
        return float(memory_value[:-2]) * 1024

    return float(memory_value) / (1024 ** 3)


def get_kubernetes_nodes():
    """
    Read real node information from the Kubernetes API.
    """

    config.load_kube_config()

    v1 = client.CoreV1Api()

    nodes = v1.list_node().items

    result = []

    for node in nodes:

        node_name = node.metadata.name

        capacity = node.status.capacity or {}
        allocatable = node.status.allocatable or {}

        cpu_capacity = parse_cpu(
            capacity.get("cpu", "0")
        )

        memory_capacity = parse_memory(
            capacity.get("memory", "0")
        )

        cpu_allocatable = parse_cpu(
            allocatable.get("cpu", "0")
        )

        memory_allocatable = parse_memory(
            allocatable.get("memory", "0")
        )

        # Count pods currently assigned to this node.
        pods = v1.list_pod_for_all_namespaces(
            field_selector=f"spec.nodeName={node_name}"
        ).items

        running_pods = sum(
            1
            for pod in pods
            if pod.status.phase == "Running"
        )

        result.append({
            "node_id": node_name,
            "cpu_capacity_cores": cpu_capacity,
            "memory_capacity_gb": memory_capacity,
            "cpu_allocatable_cores": cpu_allocatable,
            "memory_allocatable_gb": memory_allocatable,
            "running_pods": running_pods,
        })

    return result


if __name__ == "__main__":

    nodes = get_kubernetes_nodes()

    print("\n" + "=" * 70)
    print("          REAL KUBERNETES NODE INFORMATION")
    print("=" * 70)

    for node in nodes:

        print(f"\nNode: {node['node_id']}")

        print(
            f"CPU Capacity      : "
            f"{node['cpu_capacity_cores']:.2f} cores"
        )

        print(
            f"CPU Allocatable   : "
            f"{node['cpu_allocatable_cores']:.2f} cores"
        )

        print(
            f"Memory Capacity   : "
            f"{node['memory_capacity_gb']:.2f} GiB"
        )

        print(
            f"Memory Allocatable: "
            f"{node['memory_allocatable_gb']:.2f} GiB"
        )

        print(
            f"Running Pods      : "
            f"{node['running_pods']}"
        )

        print("-" * 70)

    print(
        f"\nTotal nodes discovered: {len(nodes)}"
    )
    