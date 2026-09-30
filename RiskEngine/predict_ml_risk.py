import json
import joblib
import pandas as pd

import blockchain_features as bf


# ==========================================
# Load saved ML artifacts
# ==========================================

model = joblib.load("logistic_risk_model.pkl")
scaler = joblib.load("risk_scaler.pkl")

with open("feature_columns.json", "r", encoding="utf-8") as file:
    feature_columns = json.load(file)


# ==========================================
# Use REAL blockchain-derived features
# ==========================================

transaction = bf.features


# ==========================================
# Arrange features in training order
# ==========================================

input_data = pd.DataFrame(
    [transaction],
    columns=feature_columns
)


# ==========================================
# Scale input
# ==========================================

scaled_input = scaler.transform(input_data)


# ==========================================
# ML prediction
# ==========================================

risk_probability = model.predict_proba(
    scaled_input
)[0][1]

risk_score = risk_probability * 100


# ==========================================
# AgentGuard policy
# ==========================================

if risk_probability < 0.30:
    risk_level = "LOW"
    decision = "AUTO_APPROVE"

elif risk_probability < 0.70:
    risk_level = "MEDIUM"
    decision = "EXTRA_CHECKS"

else:
    risk_level = "HIGH"
    decision = "HUMAN_APPROVAL"


# ==========================================
# Display blockchain-backed prediction
# ==========================================

print()
print("======================================")
print(" AgentGuard Blockchain + ML Risk Test")
print("======================================")

print()
print("Real Blockchain Features")
print("------------------------------")

print(
    "Transaction Amount :",
    transaction["transaction_amount"],
    "ETH"
)

print(
    "Reputation Score   :",
    transaction["reputation_score"]
)

print(
    "Successful Tx      :",
    transaction["successful_transactions"]
)

print(
    "Failed Tx          :",
    transaction["failed_transactions"]
)

print(
    "Refunded Tx        :",
    transaction["refunded_transactions"]
)

print(
    "Disputes           :",
    transaction["disputes"]
)

print(
    "Agent Age          :",
    transaction["agent_age_days"],
    "days"
)

print(
    "Amount vs History  :",
    transaction["amount_vs_history"]
)

print(
    "New Agent          :",
    bool(transaction["new_agent"])
)

print(
    "Registered         :",
    bool(transaction["is_registered"])
)

print(
    "Active             :",
    bool(transaction["is_active"])
)


print()
print("ML Risk Assessment")
print("------------------------------")

print(
    "Risk Probability :",
    round(risk_probability, 4)
)

print(
    "Risk Score       :",
    round(risk_score, 2),
    "/100"
)

print(
    "Risk Level       :",
    risk_level
)

print(
    "Decision         :",
    decision
)

print()
print("======================================")
print(" Blockchain-backed ML Prediction Done")
print("======================================")