import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    roc_auc_score
)


# ==========================================
# 1. Load dataset
# ==========================================

df = pd.read_csv("agentguard_risk_dataset.csv")

print()
print("======================================")
print(" AgentGuard ML Model Training")
print("======================================")

print()
print("Dataset shape:", df.shape)


# ==========================================
# 2. Separate features and target
# ==========================================

X = df.drop("risky", axis=1)
y = df["risky"]


# ==========================================
# 3. Train/Test split
# ==========================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print()
print("Training samples :", len(X_train))
print("Testing samples  :", len(X_test))


# ==========================================
# 4. Logistic Regression
# ==========================================

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

logistic_model = LogisticRegression(
    max_iter=1000,
    random_state=42
)

logistic_model.fit(
    X_train_scaled,
    y_train
)

logistic_predictions = logistic_model.predict(
    X_test_scaled
)

logistic_probabilities = logistic_model.predict_proba(
    X_test_scaled
)[:, 1]


# ==========================================
# 5. Random Forest
# ==========================================

random_forest_model = RandomForestClassifier(
    n_estimators=200,
    random_state=42,
    class_weight="balanced"
)

random_forest_model.fit(
    X_train,
    y_train
)

random_forest_predictions = random_forest_model.predict(
    X_test
)

random_forest_probabilities = random_forest_model.predict_proba(
    X_test
)[:, 1]


# ==========================================
# 6. Evaluation function
# ==========================================

def evaluate_model(
    name,
    y_true,
    predictions,
    probabilities
):

    accuracy = accuracy_score(
        y_true,
        predictions
    )

    precision = precision_score(
        y_true,
        predictions,
        zero_division=0
    )

    recall = recall_score(
        y_true,
        predictions,
        zero_division=0
    )

    f1 = f1_score(
        y_true,
        predictions,
        zero_division=0
    )

    auc = roc_auc_score(
        y_true,
        probabilities
    )

    matrix = confusion_matrix(
        y_true,
        predictions
    )

    print()
    print("======================================")
    print(name)
    print("======================================")

    print(
        "Accuracy  :",
        round(accuracy, 4)
    )

    print(
        "Precision :",
        round(precision, 4)
    )

    print(
        "Recall    :",
        round(recall, 4)
    )

    print(
        "F1 Score  :",
        round(f1, 4)
    )

    print(
        "ROC-AUC   :",
        round(auc, 4)
    )

    print()
    print("Confusion Matrix:")
    print(matrix)

    print()
    print("Classification Report:")

    print(
        classification_report(
            y_true,
            predictions,
            target_names=[
                "Non-Risky",
                "Risky"
            ],
            zero_division=0
        )
    )


# ==========================================
# 7. Evaluate both models
# ==========================================

evaluate_model(
    "LOGISTIC REGRESSION",
    y_test,
    logistic_predictions,
    logistic_probabilities
)

evaluate_model(
    "RANDOM FOREST",
    y_test,
    random_forest_predictions,
    random_forest_probabilities
)


# ==========================================
# 8. Random Forest feature importance
# ==========================================

importance = pd.DataFrame({
    "feature": X.columns,
    "importance": random_forest_model.feature_importances_
})

importance = importance.sort_values(
    by="importance",
    ascending=False
)


print()
print("======================================")
print(" Random Forest Feature Importance")
print("======================================")

for _, row in importance.iterrows():

    print(
        f"{row['feature']:<30} "
        f"{row['importance']:.4f}"
    )


print()
print("======================================")
print(" Training Complete")
print("======================================")
