import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from web3 import Web3


# ==========================================
# Environment
# ==========================================

load_dotenv(r"..\Blockchain\.env")

RPC_URL = os.getenv("SEPOLIA_RPC_URL")

if not RPC_URL:
    raise RuntimeError(
        "SEPOLIA_RPC_URL not found in Blockchain/.env"
    )


# ==========================================
# Contract addresses
# ==========================================

REGISTRY_ADDRESS = (
    "0xD19597a1fD327B16CbCEEb8e22D5b299AAFBe6fE"
)

REPUTATION_ADDRESS = (
    "0xE86D8823FF9E3BB2dAd8d3C73C035ED735e1f643"
)


# ==========================================
# Blockchain connection
# ==========================================

w3 = Web3(
    Web3.HTTPProvider(RPC_URL)
)

if not w3.is_connected():
    raise RuntimeError(
        "Could not connect to Ethereum Sepolia"
    )


if w3.eth.chain_id != 11155111:
    raise RuntimeError(
        f"Wrong network. Expected Sepolia (11155111), "
        f"got {w3.eth.chain_id}"
    )


# ==========================================
# Load ABIs
# ==========================================

with open(
    r"..\Blockchain\artifacts\contracts\AgentRegistry.sol\AgentRegistry.json",
    "r",
    encoding="utf-8"
) as file:
    registry_artifact = json.load(file)


with open(
    r"..\Blockchain\artifacts\contracts\Reputation.sol\Reputation.json",
    "r",
    encoding="utf-8"
) as file:
    reputation_artifact = json.load(file)


registry = w3.eth.contract(
    address=Web3.to_checksum_address(
        REGISTRY_ADDRESS
    ),
    abi=registry_artifact["abi"]
)


reputation = w3.eth.contract(
    address=Web3.to_checksum_address(
        REPUTATION_ADDRESS
    ),
    abi=reputation_artifact["abi"]
)


# ==========================================
# Read current blockchain state
# ==========================================

def get_blockchain_features(
    agent_id,
    transaction_amount
):

    if transaction_amount <= 0:
        raise ValueError(
            "Transaction amount must be greater than 0"
        )


    # --------------------------------------
    # Get agent from AgentRegistry
    # --------------------------------------

    agent = registry.functions.getAgent(
        agent_id
    ).call()

    registered_agent_id = agent[0]
    wallet = agent[1]
    service_type = agent[2]
    is_active = agent[3]
    registered_at = agent[4]


    # Check that the agent exists
    if wallet == "0x0000000000000000000000000000000000000000":
        raise ValueError(
            f"Agent '{agent_id}' is not registered"
        )


    # --------------------------------------
    # Get reputation
    # --------------------------------------

    reputation_data = reputation.functions.getReputation(
        Web3.to_checksum_address(wallet)
    ).call()

    successful_transactions = reputation_data[0]
    failed_transactions = reputation_data[1]
    refunded_transactions = reputation_data[2]
    disputes = reputation_data[3]

    total_transaction_value_wei = reputation_data[4]

    reputation_score = reputation.functions.getReputationScore(
        Web3.to_checksum_address(wallet)
    ).call()


    # --------------------------------------
    # Agent age
    # --------------------------------------

    current_timestamp = int(
        datetime.now(timezone.utc).timestamp()
    )

    age_seconds = max(
        0,
        current_timestamp - registered_at
    )

    agent_age_days = age_seconds / 86400


    # --------------------------------------
    # Historical transaction amount
    # --------------------------------------

    completed_transactions = (
        successful_transactions
        + failed_transactions
    )

    if completed_transactions > 0:

        average_historical_amount_eth = float(
            w3.from_wei(
                total_transaction_value_wei,
                "ether"
            )
        ) / completed_transactions

        if average_historical_amount_eth > 0:

            amount_vs_history = (
                transaction_amount
                / average_historical_amount_eth
            )

        else:
            amount_vs_history = 1.0

    else:

        average_historical_amount_eth = 0.0
        amount_vs_history = 1.0


    # --------------------------------------
    # Derived features
    # --------------------------------------

    new_agent = (
        1
        if agent_age_days < 30
        else 0
    )


    features = {

        "transaction_amount":
            transaction_amount,

        "reputation_score":
            reputation_score,

        "successful_transactions":
            successful_transactions,

        "failed_transactions":
            failed_transactions,

        "refunded_transactions":
            refunded_transactions,

        "disputes":
            disputes,

        "agent_age_days":
            round(agent_age_days, 4),

        "amount_vs_history":
            round(amount_vs_history, 4),

        "new_agent":
            new_agent,

        "is_registered":
            1,

        "is_active":
            1 if is_active else 0
    }


    return {
        "agent_id": registered_agent_id,
        "provider": wallet,
        "service_type": service_type,
        "active": is_active,
        "registered_at": registered_at,
        "agent_age_days": round(
            agent_age_days,
            4
        ),
        "average_historical_amount_eth":
            round(
                average_historical_amount_eth,
                6
            ),
        "features": features
    }