import json
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression


# ==========================================
# Load dataset
# ==========================================

df = pd.read_csv("agentguard_risk_dataset.csv")

X = df.drop("risky", axis=1)
y = df["risky"]


# ==========================================
# Train/test split
# ==========================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)


# ==========================================
# Scale features
# ==========================================

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(X_train)


# ==========================================
# Train Logistic Regression
# ==========================================

model = LogisticRegression(
    max_iter=1000,
    random_state=42
)

model.fit(
    X_train_scaled,
    y_train
)


# ==========================================
# Save model
# ==========================================

joblib.dump(
    model,
    "logistic_risk_model.pkl"
)

joblib.dump(
    scaler,
    "risk_scaler.pkl"
)


# ==========================================
# Save feature order
# ==========================================

feature_columns = list(X.columns)

with open("feature_columns.json", "w") as file:
    json.dump(
        feature_columns,
        file,
        indent=4
    )


print()
print("======================================")
print(" AgentGuard ML Model Saved")
print("======================================")

print()
print("Model:")
print("logistic_risk_model.pkl")

print()
print("Scaler:")
print("risk_scaler.pkl")

print()
print("Feature definition:")
print("feature_columns.json")

print()
print("Features used:")
for feature in feature_columns:
    print("-", feature)

print()
print("Model artifacts saved successfully.")