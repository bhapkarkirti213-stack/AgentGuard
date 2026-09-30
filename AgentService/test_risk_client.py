from risk_client import assess_transaction_risk


def print_result(amount, result):

    print()
    print("======================================")
    print(" AgentService → Risk Engine Test")
    print("======================================")

    print(
        "Transaction Amount :",
        amount,
        "ETH"
    )

    print(
        "Agent ID           :",
        result["agent_id"]
    )

    print(
        "Provider           :",
        result["provider"]
    )

    print(
        "Reputation         :",
        result["reputation_score"]
    )

    print(
        "Successful Tx      :",
        result["successful_transactions"]
    )

    print(
        "Failed Tx          :",
        result["failed_transactions"]
    )

    print(
        "Refunded Tx        :",
        result["refunded_transactions"]
    )

    print(
        "Disputes           :",
        result["disputes"]
    )

    print(
        "Agent Age          :",
        result["agent_age_days"]
    )

    print(
        "Amount vs History  :",
        result["amount_vs_history"]
    )

    print()
    print("Risk Assessment")
    print("------------------------------")

    print(
        "Risk Probability :",
        result["risk_probability"]
    )

    print(
        "Risk Score       :",
        result["risk_score"],
        "/100"
    )

    print(
        "Risk Level       :",
        result["risk_level"]
    )

    print(
        "Decision         :",
        result["decision"]
    )


if __name__ == "__main__":

    result = assess_transaction_risk(
        "weather-agent-sepolia",
        0.001
    )

    print_result(
        0.001,
        result
    )