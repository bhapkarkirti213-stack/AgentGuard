import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from web3 import Web3


# ==========================================
# Configuration
# ==========================================

load_dotenv(r"..\Blockchain\.env")

RPC_URL = os.getenv("SEPOLIA_RPC_URL")

if not RPC_URL:
    raise ValueError("SEPOLIA_RPC_URL not found in Blockchain/.env")


REGISTRY_ADDRESS = "0xD19597a1fD327B16CbCEEb8e22D5b299AAFBe6fE"
REPUTATION_ADDRESS = "0xE86D8823FF9E3BB2dAd8d3C73C035ED735e1f643"

PROVIDER_ADDRESS = "0x570CE7B44af68e53F6e219493a46b4DAf6812B98"
AGENT_ID = "weather-agent-sepolia"

CURRENT_TRANSACTION_AMOUNT = 0.001


# ==========================================
# Connect to Sepolia
# ==========================================

w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    raise ConnectionError("Could not connect to Ethereum Sepolia")

chain_id = w3.eth.chain_id

if chain_id != 11155111:
    raise ValueError(
        f"Wrong network. Expected Sepolia 11155111, got {chain_id}"
    )


# ==========================================
# Load contract ABIs
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
    address=Web3.to_checksum_address(REGISTRY_ADDRESS),
    abi=registry_artifact["abi"]
)


reputation = w3.eth.contract(
    address=Web3.to_checksum_address(REPUTATION_ADDRESS),
    abi=reputation_artifact["abi"]
)


# ==========================================
# Read AgentRegistry
# ==========================================

agent = registry.functions.getAgent(AGENT_ID).call()

agent_id = agent[0]
wallet = agent[1]
service_type = agent[2]
is_active = agent[3]
registered_at = agent[4]


# ==========================================
# Read Reputation
# ==========================================

reputation_data = reputation.functions.getReputation(
    Web3.to_checksum_address(PROVIDER_ADDRESS)
).call()

successful_transactions = reputation_data[0]
failed_transactions = reputation_data[1]
refunded_transactions = reputation_data[2]
disputes = reputation_data[3]
total_transaction_value_wei = reputation_data[4]
successful_transaction_value_wei = reputation_data[5]
last_updated = reputation_data[6]

reputation_score = reputation.functions.getReputationScore(
    Web3.to_checksum_address(PROVIDER_ADDRESS)
).call()


# ==========================================
# Calculate derived features
# ==========================================

now_timestamp = int(datetime.now(timezone.utc).timestamp())

age_seconds = max(
    0,
    now_timestamp - registered_at
)

agent_age_days = age_seconds / 86400


completed_transactions = (
    successful_transactions +
    failed_transactions
)


if completed_transactions > 0:
    average_historical_amount_wei = (
        total_transaction_value_wei /
        completed_transactions
    )

    average_historical_amount_eth = (
        average_historical_amount_wei /
        10**18
    )

    if average_historical_amount_eth > 0:
        amount_vs_history = (
            CURRENT_TRANSACTION_AMOUNT /
            average_historical_amount_eth
        )
    else:
        amount_vs_history = 1.0

else:
    average_historical_amount_eth = 0.0
    amount_vs_history = 1.0


new_agent = 1 if agent_age_days < 30 else 0


# ==========================================
# Build ML feature object
# ==========================================

features = {
    "transaction_amount": CURRENT_TRANSACTION_AMOUNT,
    "reputation_score": reputation_score,
    "successful_transactions": successful_transactions,
    "failed_transactions": failed_transactions,
    "refunded_transactions": refunded_transactions,
    "disputes": disputes,
    "agent_age_days": round(agent_age_days, 4),
    "amount_vs_history": round(amount_vs_history, 4),
    "new_agent": new_agent,
    "is_registered": 1 if wallet != "0x0000000000000000000000000000000000000000" else 0,
    "is_active": 1 if is_active else 0
}


# ==========================================
# Display blockchain evidence
# ==========================================

print()
print("======================================")
print(" AgentGuard Blockchain Feature Reader")
print("======================================")

print()
print("Network")
print("------------------------------")
print("Chain ID       :", chain_id)
print("Provider       :", PROVIDER_ADDRESS)
print("Agent ID       :", agent_id)
print("Service Type   :", service_type)

print()
print("On-Chain Agent Data")
print("------------------------------")
print("Registered At  :", registered_at)
print(
    "Registration Time:",
    datetime.fromtimestamp(
        registered_at,
        timezone.utc
    ).isoformat()
)
print("Agent Age      :", round(agent_age_days, 4), "days")
print("Active         :", is_active)

print()
print("On-Chain Reputation")
print("------------------------------")
print("Successful Tx  :", successful_transactions)
print("Failed Tx      :", failed_transactions)
print("Refunded Tx    :", refunded_transactions)
print("Disputes       :", disputes)
print("Total Value    :", w3.from_wei(
    total_transaction_value_wei,
    "ether"
), "ETH")
print("Reputation     :", reputation_score)

print()
print("Derived ML Features")
print("------------------------------")

for name, value in features.items():
    print(f"{name:<25}: {value}")

print()
print("Average Historical Amount:",
      round(average_historical_amount_eth, 6),
      "ETH")

print()
print("Blockchain feature extraction successful.")
