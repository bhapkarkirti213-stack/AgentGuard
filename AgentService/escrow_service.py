import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
BLOCKCHAIN_DIR = BASE_DIR.parent / "Blockchain"


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv(BASE_DIR / ".env")
load_dotenv(
    BLOCKCHAIN_DIR / ".env",
    override=False
)

RPC_URL = os.getenv(
    "SEPOLIA_RPC_URL"
)

PRIVATE_KEY = os.getenv(
    "SEPOLIA_PRIVATE_KEY"
)

CHAIN_ID_VALUE = os.getenv(
    "SEPOLIA_CHAIN_ID"
)

REGISTRY_ADDRESS = os.getenv(
    "AGENT_REGISTRY_ADDRESS"
)

ESCROW_ADDRESS = os.getenv(
    "ESCROW_CONTRACT_ADDRESS"
)


# =========================================================
# CONFIGURATION VALIDATION
# =========================================================

required_configuration = {
    "SEPOLIA_RPC_URL": RPC_URL,
    "SEPOLIA_PRIVATE_KEY": PRIVATE_KEY,
    "SEPOLIA_CHAIN_ID": CHAIN_ID_VALUE,
    "AGENT_REGISTRY_ADDRESS": REGISTRY_ADDRESS,
    "ESCROW_CONTRACT_ADDRESS": ESCROW_ADDRESS,
}

missing_configuration = [
    name
    for name, value in required_configuration.items()
    if not value
]

if missing_configuration:
    raise RuntimeError(
        "Missing configuration: "
        + ", ".join(missing_configuration)
    )

try:
    CHAIN_ID = int(
        CHAIN_ID_VALUE
    )
except ValueError as exc:
    raise RuntimeError(
        "SEPOLIA_CHAIN_ID must be an integer"
    ) from exc


# =========================================================
# WEB3 CONNECTION
# =========================================================

w3 = Web3(
    Web3.HTTPProvider(
        RPC_URL,
        request_kwargs={
            "timeout": 30
        }
    )
)


if not w3.is_connected():
    raise RuntimeError(
        "Could not connect to Ethereum network"
    )


if w3.eth.chain_id != CHAIN_ID:
    raise RuntimeError(
        f"Wrong blockchain network. "
        f"Expected chain ID {CHAIN_ID}, "
        f"got {w3.eth.chain_id}"
    )


# =========================================================
# BUYER WALLET
# =========================================================

account = Account.from_key(
    PRIVATE_KEY
)

BUYER_WALLET = account.address


# =========================================================
# LOAD SMART-CONTRACT ABIS
# =========================================================

REGISTRY_ARTIFACT = (
    BLOCKCHAIN_DIR
    / "artifacts"
    / "contracts"
    / "AgentRegistry.sol"
    / "AgentRegistry.json"
)

ESCROW_ARTIFACT = (
    BLOCKCHAIN_DIR
    / "artifacts"
    / "contracts"
    / "Escrow.sol"
    / "Escrow.json"
)


if not REGISTRY_ARTIFACT.exists():
    raise RuntimeError(
        "AgentRegistry artifact not found"
    )


if not ESCROW_ARTIFACT.exists():
    raise RuntimeError(
        "Escrow artifact not found"
    )


with open(
    REGISTRY_ARTIFACT,
    "r",
    encoding="utf-8"
) as file:
    registry_artifact = json.load(
        file
    )


with open(
    ESCROW_ARTIFACT,
    "r",
    encoding="utf-8"
) as file:
    escrow_artifact = json.load(
        file
    )


# =========================================================
# CONTRACT OBJECTS
# =========================================================

registry = w3.eth.contract(
    address=Web3.to_checksum_address(
        REGISTRY_ADDRESS
    ),
    abi=registry_artifact["abi"]
)


escrow = w3.eth.contract(
    address=Web3.to_checksum_address(
        ESCROW_ADDRESS
    ),
    abi=escrow_artifact["abi"]
)


# =========================================================
# REQUEST HASH
# =========================================================

def create_request_hash(
    service_request
):
    """
    Create a deterministic keccak256 hash from
    the runtime service request.
    """

    canonical_json = json.dumps(
        service_request,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    )

    request_hash = Web3.keccak(
        text=canonical_json
    )

    return (
        request_hash,
        canonical_json
    )


# =========================================================
# EXTRACT ESCROW ID FROM BLOCKCHAIN EVENT
# =========================================================

def extract_escrow_id(
    receipt
):
    """
    Extract the actual escrow ID emitted by the
    EscrowCreated event.

    The ID is obtained from the blockchain and
    is never hardcoded.
    """

    events = (
        escrow
        .events
        .EscrowCreated()
        .process_receipt(
            receipt
        )
    )

    if not events:
        raise RuntimeError(
            "EscrowCreated event not found"
        )

    escrow_id = (
        events[0]["args"]["escrowId"]
    )

    return int(
        escrow_id
    )


# =========================================================
# READ ESCROW FROM BLOCKCHAIN
# =========================================================

def get_escrow(
    escrow_id
):
    """
    Read an escrow directly from the
    deployed Escrow smart contract.
    """

    return escrow.functions.getEscrow(
        int(escrow_id)
    ).call()


# =========================================================
# CREATE REAL ESCROW
# =========================================================

def create_escrow(
    agent_id,
    transaction_amount,
    service_request,
    deadline=None
):

    # -----------------------------------------------------
    # Validate amount
    # -----------------------------------------------------

    if transaction_amount <= 0:
        raise ValueError(
            "Transaction amount must be greater than 0"
        )


    # -----------------------------------------------------
    # Read provider dynamically from AgentRegistry
    # -----------------------------------------------------

    agent = registry.functions.getAgent(
        agent_id
    ).call()

    provider = agent[1]
    service_type = agent[2]
    active = agent[3]

    zero_address = (
        "0x0000000000000000000000000000000000000000"
    )


    if (
        provider.lower()
        == zero_address.lower()
    ):
        raise ValueError(
            f"Agent '{agent_id}' is not registered"
        )


    if not active:
        raise ValueError(
            f"Agent '{agent_id}' is inactive"
        )


    # -----------------------------------------------------
    # Generate request hash dynamically
    # -----------------------------------------------------

    request_hash, canonical_json = (
        create_request_hash(
            service_request
        )
    )


    # -----------------------------------------------------
    # Generate deadline dynamically if not supplied
    # -----------------------------------------------------

    current_timestamp = int(
        datetime.now(
            timezone.utc
        ).timestamp()
    )


    if deadline is None:
        deadline = (
            current_timestamp
            + 3600
        )


    deadline = int(
        deadline
    )


    if deadline <= current_timestamp:
        raise ValueError(
            "Deadline must be in the future"
        )


    # -----------------------------------------------------
    # Convert ETH to Wei
    # -----------------------------------------------------

    amount_wei = w3.to_wei(
        str(transaction_amount),
        "ether"
    )


    # -----------------------------------------------------
    # Build smart-contract function call
    # -----------------------------------------------------

    function_call = (
        escrow
        .functions
        .createEscrow(
            agent_id,
            Web3.to_checksum_address(
                provider
            ),
            request_hash,
            deadline
        )
    )


    # -----------------------------------------------------
    # Estimate gas dynamically
    # -----------------------------------------------------

    estimated_gas = (
        function_call
        .estimate_gas(
            {
                "from":
                    BUYER_WALLET,
                "value":
                    amount_wei
            }
        )
    )


    gas_limit = int(
        estimated_gas * 1.20
    )


    # -----------------------------------------------------
    # Get pending nonce dynamically
    # -----------------------------------------------------

    nonce = (
        w3
        .eth
        .get_transaction_count(
            BUYER_WALLET,
            "pending"
        )
    )


    # -----------------------------------------------------
    # Get current gas price dynamically
    # -----------------------------------------------------

    gas_price = (
        w3
        .eth
        .gas_price
    )


    # -----------------------------------------------------
    # Build transaction
    # -----------------------------------------------------

    transaction = (
        function_call
        .build_transaction(
            {
                "from":
                    BUYER_WALLET,

                "nonce":
                    nonce,

                "chainId":
                    w3.eth.chain_id,

                "gas":
                    gas_limit,

                "gasPrice":
                    gas_price,

                "value":
                    amount_wei
            }
        )
    )


    # -----------------------------------------------------
    # Sign transaction
    # -----------------------------------------------------

    signed_transaction = (
        account
        .sign_transaction(
            transaction
        )
    )


    # -----------------------------------------------------
    # Send REAL Sepolia transaction
    # -----------------------------------------------------

    tx_hash = (
        w3
        .eth
        .send_raw_transaction(
            signed_transaction.raw_transaction
        )
    )


    # -----------------------------------------------------
    # Wait for blockchain confirmation
    # -----------------------------------------------------

    receipt = (
        w3
        .eth
        .wait_for_transaction_receipt(
            tx_hash
        )
    )


    if receipt.status != 1:
        raise RuntimeError(
            "Escrow transaction failed on blockchain"
        )


    # -----------------------------------------------------
    # Extract REAL escrow ID from event
    # -----------------------------------------------------

    escrow_id = (
        extract_escrow_id(
            receipt
        )
    )


    # -----------------------------------------------------
    # Read created escrow from blockchain
    # -----------------------------------------------------

    on_chain_escrow = (
        get_escrow(
            escrow_id
        )
    )


    # -----------------------------------------------------
    # Extract on-chain values
    # -----------------------------------------------------

    on_chain_buyer = (
        on_chain_escrow[0]
    )

    on_chain_provider = (
        on_chain_escrow[1]
    )

    on_chain_agent_id = (
        on_chain_escrow[2]
    )

    on_chain_amount = (
        on_chain_escrow[3]
    )

    on_chain_service_hash = (
        on_chain_escrow[4]
    )

    on_chain_created_at = (
        on_chain_escrow[5]
    )

    on_chain_deadline = (
        on_chain_escrow[6]
    )

    on_chain_status = (
        on_chain_escrow[7]
    )


    # -----------------------------------------------------
    # Verify buyer
    # -----------------------------------------------------

    if (
        Web3.to_checksum_address(
            on_chain_buyer
        )
        != Web3.to_checksum_address(
            BUYER_WALLET
        )
    ):
        raise RuntimeError(
            "On-chain buyer does not match wallet"
        )


    # -----------------------------------------------------
    # Verify provider
    # -----------------------------------------------------

    if (
        Web3.to_checksum_address(
            on_chain_provider
        )
        != Web3.to_checksum_address(
            provider
        )
    ):
        raise RuntimeError(
            "On-chain provider does not match registered agent"
        )


    # -----------------------------------------------------
    # Verify agent ID
    # -----------------------------------------------------

    if (
        on_chain_agent_id
        != agent_id
    ):
        raise RuntimeError(
            "On-chain agent ID does not match request"
        )


    # -----------------------------------------------------
    # Verify amount
    # -----------------------------------------------------

    if (
        on_chain_amount
        != amount_wei
    ):
        raise RuntimeError(
            "On-chain amount does not match transaction amount"
        )


    # -----------------------------------------------------
    # Verify request hash
    # -----------------------------------------------------

    if (
        on_chain_service_hash.hex()
        != request_hash.hex()
    ):
        raise RuntimeError(
            "On-chain service hash does not match request"
        )


    # -----------------------------------------------------
    # Verify deadline
    # -----------------------------------------------------

    if (
        on_chain_deadline
        != deadline
    ):
        raise RuntimeError(
            "On-chain deadline does not match request"
        )


    # -----------------------------------------------------
    # Verify current status
    # -----------------------------------------------------

    # Escrow status:
    # 0 = Created
    # 1 = Funded
    # 2 = Released
    # 3 = Refunded

    if on_chain_status != 1:
        raise RuntimeError(
            f"Unexpected escrow status: {on_chain_status}"
        )


    # -----------------------------------------------------
    # Return blockchain evidence
    # -----------------------------------------------------

    return {

        "success":
            True,

        "network":
            "Ethereum Sepolia",

        "chain_id":
            w3.eth.chain_id,

        "buyer":
            BUYER_WALLET,

        "provider":
            provider,

        "agent_id":
            agent_id,

        "service_type":
            service_type,

        "amount_eth":
            transaction_amount,

        "amount_wei":
            amount_wei,

        "escrow_id":
            escrow_id,

        "request_hash":
            request_hash.hex(),

        "canonical_request":
            canonical_json,

        "created_at":
            on_chain_created_at,

        "deadline":
            on_chain_deadline,

        "status":
            on_chain_status,

        "transaction_hash":
            tx_hash.hex(),

        "block_number":
            receipt.blockNumber,

        "gas_used":
            receipt.gasUsed
    }