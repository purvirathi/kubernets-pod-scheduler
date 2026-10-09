# Kubernetes Pod Scheduler with FCFS, Round Robin, and AI

This project demonstrates Kubernetes-style pod placement with three scheduling
algorithms:

- First Come First Serve: selects the first feasible node in cluster order.
- Round Robin: rotates through nodes to distribute pods.
- AI Scheduler: ranks feasible nodes with the trained ML model, with a safe
  heuristic fallback when the model cannot run on a local Windows setup.

The Flask backend can use a live Kubernetes cluster when available. If no
cluster is reachable, it automatically switches to a three-node simulation with
multi-container demo pods so the visualization remains presentation-ready.

## Goal
Given a Pod's resource requirements and the current condition of several
Kubernetes Nodes, recommend a suitable Node.

## Folder contents
- scheduler_dataset.csv — synthetic dataset
- generate_dataset.py — regenerate dataset
- train_model.py — retrain Random Forest
- scheduler_model.joblib — trained model
- predict_node.py — prediction/recommendation function
- demo.py — working example
- model_metrics.txt — evaluation results
- feature_importance.png — report screenshot
- confusion_matrix.png — report screenshot
- member1_report_notes.md — report/viva material
- requirements.txt — dependencies
- QUICKSTART.txt — quick commands

## Run the Full Demo

Backend:

```bash
python -m pip install -r requirements.txt
python backend_api.py
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL, usually `http://localhost:5173`.

## Demo Flow for Presentation

1. Open Dashboard to show the cluster overview.
2. Open Scheduler Lab and choose FCFS, Round Robin, or AI Scheduler.
3. Pick a workload profile. Each profile contains at least three containers.
4. Schedule the pod and compare candidate node scores.
5. Open Visualization to show which node received the pod and which containers
   are inside it.
6. Open Analytics to explain resource usage and scheduling counts.

## Docker / Kubernetes Node Guidance

In Docker Desktop or kind/minikube, create three worker nodes for the clearest
demo. For kind, the cluster config should contain three worker entries, for
example:

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
  - role: worker
```

Then recreate the cluster from that config. The app will show the live nodes
when Kubernetes is reachable; otherwise it shows the built-in three-node
simulation.

## ML Module Commands

```bash
python demo.py
```

To retrain:
python train_model.py

To generate a new dataset:
python generate_dataset.py

## Handoff to scheduler teammate
Use:

from predict_node import recommend_node
result = recommend_node(pod, nodes)
print(result["recommended_node"])

## Important
This is a college prototype using synthetic data. Real Kubernetes telemetry
and placement outcomes should replace the synthetic dataset for a production-
quality model.

# Kubernetes Pod Scheduler with AI

## Member 2 — Kubernetes and AI Scheduling Layer

### Overview

This module integrates the machine-learning model with a live Kubernetes
cluster to perform AI-assisted Pod scheduling.

The scheduler collects real Kubernetes node information, applies
Kubernetes scheduling constraints, uses the Random Forest model to rank
valid nodes, and binds the selected Pod to the recommended node.

---

## Architecture

Kubernetes Cluster
        ↓
Metrics Server
        ↓
Kubernetes Python Client
        ↓
Node Feature Adapter
        ↓
Kubernetes Constraints
        ↓
Random Forest AI Model
        ↓
Node Ranking
        ↓
Custom AI Scheduler
        ↓
Kubernetes Binding API
        ↓
Running Pod

---

## Member 2 Components

### `k8s_test.py`
Connects to the Kubernetes cluster and discovers cluster nodes.

### `k8s_node_adapter.py`
Retrieves Kubernetes node capacity and running Pod information.

### `k8s_model_adapter.py`
Converts live Kubernetes node information into the feature format
required by the AI model.

### `live_scheduler.py`
Runs the AI model against live Kubernetes node data and displays
the recommended node.

### `ai_scheduler_controller.py`
Implements the custom Kubernetes scheduler.

It:
- detects Pending Pods assigned to `ai-scheduler`
- reads Pod CPU and memory requests
- retrieves live node information
- applies scheduling constraints
- ranks valid nodes using the AI model
- binds the Pod to the selected node

### `ai-scheduler-pod.yaml`
Defines a test Pod using:

`schedulerName: ai-scheduler`

---

## Scheduling Logic

The scheduler follows a two-stage decision process:

1. Kubernetes constraints are treated as hard constraints.
2. The AI model ranks the remaining valid nodes.

A node with a `NoSchedule` taint or insufficient resources is not
selected even if its AI score would otherwise be high.

---

## Running the Scheduler

Install dependencies:

```bash
pip install -r requirements.txt
