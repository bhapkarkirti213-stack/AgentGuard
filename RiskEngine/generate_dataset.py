import math
import random
import pandas as pd

random.seed(42)
NUM_SAMPLES = 3000

def sigmoid(x):
    return 1 / (1 + math.exp(-x))

rows = []

for _ in range(NUM_SAMPLES):
    transaction_amount = round(10 ** random.uniform(-3, 0.5), 4)
    reputation_score = random.randint(0, 100)
    successful_transactions = random.randint(0, 30)
    failed_transactions = random.randint(0, 10)
    refunded_transactions = random.randint(0, 5)
    disputes = random.randint(0, 4)
    agent_age_days = random.randint(1, 1000)
    is_registered = random.random() > 0.05
    is_active = random.random() > 0.08

    average_historical_amount = round(random.uniform(0.005, 1.0), 4)
    amount_vs_history = round(
        transaction_amount / average_historical_amount,
        3
    )
    new_agent = agent_age_days < 30

    # Simulated development label, not real blockchain ground truth.
    risk_signal = -3.8

    if transaction_amount > 0.5:
        risk_signal += 1.2
    if transaction_amount > 1.5:
        risk_signal += 1.0
    if amount_vs_history > 3:
        risk_signal += 1.4
    if amount_vs_history > 6:
        risk_signal += 1.0

    if reputation_score < 40:
        risk_signal += 1.5
    elif reputation_score < 70:
        risk_signal += 0.5

    risk_signal += failed_transactions * 0.22
    risk_signal += refunded_transactions * 0.30
    risk_signal += disputes * 0.45

    if not is_registered:
        risk_signal += 1.5
    if not is_active:
        risk_signal += 1.0
    if new_agent:
        risk_signal += 0.7

    risk_signal -= successful_transactions * 0.03

    probability = sigmoid(risk_signal)
    risky = 1 if random.random() < probability else 0

    rows.append({
        "transaction_amount": transaction_amount,
        "reputation_score": reputation_score,
        "successful_transactions": successful_transactions,
        "failed_transactions": failed_transactions,
        "refunded_transactions": refunded_transactions,
        "disputes": disputes,
        "agent_age_days": agent_age_days,
        "amount_vs_history": amount_vs_history,
        "new_agent": int(new_agent),
        "is_registered": int(is_registered),
        "is_active": int(is_active),
        "risky": risky,
    })

df = pd.DataFrame(rows)
df.to_csv("agentguard_risk_dataset.csv", index=False)

print()
print("======================================")
print(" AgentGuard ML Dataset Generator")
print("======================================")
print()
print("Dataset created successfully.")
print("Number of samples :", len(df))
print("Number of features:", len(df.columns) - 1)
print()
print("Class distribution:")
print(df["risky"].value_counts().sort_index())
print()
print("Risky transaction percentage:",
      round(df["risky"].mean() * 100, 2), "%")
print()
print("Dataset columns:")
for column in df.columns:
    print("-", column)
print()
print("First 5 rows:")
print(df.head())
print()
print("Saved as:")
print("agentguard_risk_dataset.csv")

