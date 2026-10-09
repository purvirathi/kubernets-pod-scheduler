from pathlib import Path
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

BASE = Path(__file__).parent
DATA_PATH = BASE / "scheduler_dataset.csv"
MODEL_PATH = BASE / "scheduler_model.joblib"

FEATURE_COLUMNS = [
    "pod_cpu_request",
    "pod_memory_request_gb",
    "node_cpu_capacity_cores",
    "node_memory_capacity_gb",
    "cpu_utilization_pct",
    "memory_utilization_pct",
    "available_cpu_cores",
    "available_memory_gb",
    "running_pods",
    "post_cpu_utilization_pct",
    "post_memory_utilization_pct",
    "cpu_headroom_ratio",
    "memory_headroom_ratio",
    "feasible",
]

def main():
    df = pd.read_csv(DATA_PATH)
    X = df[FEATURE_COLUMNS]
    y = df["recommended"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    print("\nClassification report:")
    print(classification_report(y_test, y_pred, digits=4))
    print("\nConfusion matrix:")
    print(confusion_matrix(y_test, y_pred))

    joblib.dump(
        {"model": model, "feature_columns": FEATURE_COLUMNS},
        MODEL_PATH
    )
    print(f"\nSaved model to: {MODEL_PATH}")

if __name__ == "__main__":
    main()
