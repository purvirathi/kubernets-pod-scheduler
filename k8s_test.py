from kubernetes import client, config


def get_cluster_nodes():
    # Load the Kubernetes configuration from the local kubeconfig.
    config.load_kube_config()

    # Create a connection to the Kubernetes API.
    v1 = client.CoreV1Api()

    # Ask Kubernetes for all nodes.
    nodes = v1.list_node().items

    print("\n" + "=" * 60)
    print("          KUBERNETES CLUSTER NODES")
    print("=" * 60)

    for node in nodes:
        node_name = node.metadata.name

        # Kubernetes reports the node's current condition.
        conditions = node.status.conditions or []

        ready_status = "Unknown"

        for condition in conditions:
            if condition.type == "Ready":
                ready_status = condition.status

        print(f"Node   : {node_name}")
        print(f"Ready  : {ready_status}")
        print("-" * 60)

    print(f"Total nodes discovered: {len(nodes)}")


if __name__ == "__main__":
    get_cluster_nodes()