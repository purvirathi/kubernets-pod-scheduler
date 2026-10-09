# Member 1 — AI/ML Report Notes

## Objective
Build an AI/ML module that recommends a suitable Kubernetes node for a Pod.

## Model
Random Forest Classifier.

## Why Random Forest?
- Good for tabular data.
- Handles non-linear relationships.
- Easy to train and integrate.
- Provides feature importance.

## Inputs
Pod CPU request, Pod memory request, node CPU/memory capacity, CPU/memory
utilization, available CPU/memory, running Pod count, projected post-placement
utilization, headroom ratios, and a basic feasibility indicator.

## Output
For each candidate node, the model estimates the probability that the node is
a good recommendation. The prediction function chooses the highest-scoring
feasible node.

## ML pipeline
Dataset → feature preparation → train/test split → Random Forest → evaluation
→ saved model → prediction function.

## Important limitation
The current dataset is synthetic. Its labels are produced by a transparent
resource-aware rule. Therefore model accuracy demonstrates learning of the
prototype labeling pattern, not proof that it outperforms Kubernetes' real
scheduler.

## Team handoff
Share:
- scheduler_model.joblib
- predict_node.py
- requirements.txt

The integration teammate can call:

from predict_node import recommend_node
result = recommend_node(pod, nodes)
recommended = result["recommended_node"]
