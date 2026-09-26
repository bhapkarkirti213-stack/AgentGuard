def calculate_risk(transaction):
    risk = 0
    reasons = []

    # 1. Agent registration
    if not transaction["is_registered"]:
        risk += 30
        reasons.append("Agent is not registered")
    else:
        reasons.append("Agent is registered")

    # 2. Agent active status
    if not transaction["is_active"]:
        risk += 20
        reasons.append("Agent is inactive")
    else:
        reasons.append("Agent is active")

    # 3. Agent reputation
    reputation = transaction["reputation_score"]

    if reputation < 30:
        risk += 25
        reasons.append("Very low reputation")
    elif reputation < 60:
        risk += 15
        reasons.append("Low reputation")
    elif reputation < 80:
        risk += 5
        reasons.append("Moderate reputation")
    else:
        reasons.append("High reputation")

    # 4. Failed transactions
    failed = transaction["failed_transactions"]

    if failed >= 5:
        risk += 20
        reasons.append("Many previous failures")
    elif failed > 0:
        risk += 10
        reasons.append("Previous transaction failures")
    else:
        reasons.append("No previous failures")

    # 5. Refunded transactions
    refunds = transaction["refunded_transactions"]

    if refunds >= 3:
        risk += 15
        reasons.append("Multiple refunds")
    elif refunds > 0:
        risk += 8
        reasons.append("Previous refunds")
    else:
        reasons.append("No previous refunds")

    # 6. Disputes
    disputes = transaction["disputes"]

    if disputes >= 2:
        risk += 15
        reasons.append("Multiple disputes")
    elif disputes > 0:
        risk += 10
        reasons.append("Previous dispute")
    else:
        reasons.append("No previous disputes")

    # 7. Transaction amount
    amount = transaction["transaction_amount"]

    if amount > 1:
        risk += 20
        reasons.append("Very large transaction")
    elif amount > 0.1:
        risk += 10
        reasons.append("Large transaction")
    else:
        reasons.append("Transaction amount is within normal range")

    # Keep risk score between 0 and 100
    risk = min(risk, 100)

    # Determine risk level and action
    if risk < 30:
        risk_level = "LOW"
        decision = "AUTO_APPROVE"
    elif risk < 70:
        risk_level = "MEDIUM"
        decision = "EXTRA_CHECKS"
    else:
        risk_level = "HIGH"
        decision = "HUMAN_APPROVAL"

    return {
        "risk_score": risk,
        "risk_level": risk_level,
        "decision": decision,
        "reasons": reasons
    }


def print_result(title, transaction, result):
    print()
    print("======================================")
    print(title)
    print("======================================")

    print("Transaction Amount :", transaction["transaction_amount"], "ETH")
    print("Reputation Score   :", transaction["reputation_score"])
    print("Successful Tx      :", transaction["successful_transactions"])
    print("Failed Tx          :", transaction["failed_transactions"])
    print("Refunded Tx        :", transaction["refunded_transactions"])
    print("Disputes           :", transaction["disputes"])
    print("Registered         :", transaction["is_registered"])
    print("Active             :", transaction["is_active"])

    print()
    print("Risk Assessment")
    print("------------------------------")
    print("Risk Score :", str(result["risk_score"]) + "/100")
    print("Risk Level :", result["risk_level"])
    print("Decision   :", result["decision"])

    print()
    print("Reasons:")

    for reason in result["reasons"]:
        print("-", reason)


if __name__ == "__main__":

    # TEST CASE 1: TRUSTED AGENT
    trusted_transaction = {
        "transaction_amount": 0.001,
        "reputation_score": 100,
        "successful_transactions": 1,
        "failed_transactions": 0,
        "refunded_transactions": 0,
        "disputes": 0,
        "is_registered": True,
        "is_active": True
    }

    trusted_result = calculate_risk(trusted_transaction)

    print_result(
        "TEST CASE 1 - TRUSTED AGENT",
        trusted_transaction,
        trusted_result
    )

    # TEST CASE 2: MEDIUM-RISK AGENT
    medium_transaction = {
        "transaction_amount": 0.2,
        "reputation_score": 65,
        "successful_transactions": 5,
        "failed_transactions": 1,
        "refunded_transactions": 1,
        "disputes": 0,
        "is_registered": True,
        "is_active": True
    }

    medium_result = calculate_risk(medium_transaction)

    print_result(
        "TEST CASE 2 - MEDIUM-RISK AGENT",
        medium_transaction,
        medium_result
    )

    # TEST CASE 3: HIGH-RISK AGENT
    risky_transaction = {
        "transaction_amount": 2.5,
        "reputation_score": 25,
        "successful_transactions": 2,
        "failed_transactions": 6,
        "refunded_transactions": 3,
        "disputes": 2,
        "is_registered": True,
        "is_active": True
    }

    risky_result = calculate_risk(risky_transaction)

    print_result(
        "TEST CASE 3 - HIGH-RISK AGENT",
        risky_transaction,
        risky_result
    )
