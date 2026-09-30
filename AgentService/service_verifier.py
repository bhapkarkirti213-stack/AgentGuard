import json
import os
from pathlib import Path

from eth_account import Account
from dotenv import load_dotenv
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
load_dotenv(BLOCKCHAIN_DIR / ".env", override=False)

RPC_URL = os.getenv("SEPOLIA_RPC_URL")
PRIVATE_KEY = os.getenv("SEPOLIA_PRIVATE_KEY")
CHAIN_ID = int(
    os.getenv("SEPOLIA_CHAIN_ID", "11155111")
)

REGISTRY_ADDRESS = os.getenv(
    "AGENT_REGISTRY_ADDRESS"
)

ESCROW_ADDRESS = os.getenv(
    "ESCROW_CONTRACT_ADDRESS"
)

SERVICE_VERIFIER_ADDRESS = os.getenv(
    "SERVICE_VERIFIER_ADDRESS"
)


# =========================================================
# REQUIRED CONFIGURATION CHECK
# =========================================================

required_configuration = {
    "SEPOLIA_RPC_URL": RPC_URL,
    "SEPOLIA_PRIVATE_KEY": PRIVATE_KEY,
    "AGENT_REGISTRY_ADDRESS": REGISTRY_ADDRESS,
    "ESCROW_CONTRACT_ADDRESS": ESCROW_ADDRESS,
    "SERVICE_VERIFIER_ADDRESS": SERVICE_VERIFIER_ADDRESS,
}

missing = [
    name
    for name, value in required_configuration.items()
    if not value
]

if missing:
    raise RuntimeError(
        "Missing configuration: "
        + ", ".join(missing)
    )


# =========================================================
# WEB3
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
        "Could not connect to Ethereum Sepolia"
    )

if w3.eth.chain_id != CHAIN_ID:
    raise RuntimeError(
        f"Wrong blockchain network. "
        f"Expected {CHAIN_ID}, "
        f"got {w3.eth.chain_id}"
    )


# =========================================================
# WALLET
# =========================================================

account = Account.from_key(
    PRIVATE_KEY
)

WALLET_ADDRESS = account.address


# =========================================================
# LOAD ABIS
# =========================================================

ESCROW_ARTIFACT = (
    BLOCKCHAIN_DIR
    / "artifacts"
    / "contracts"
    / "Escrow.sol"
    / "Escrow.json"
)

VERIFIER_ARTIFACT = (
    BLOCKCHAIN_DIR
    / "artifacts"
    / "contracts"
    / "ServiceVerifier.sol"
    / "ServiceVerifier.json"
)

if not ESCROW_ARTIFACT.exists():
    raise RuntimeError(
        "Escrow artifact not found"
    )

if not VERIFIER_ARTIFACT.exists():
    raise RuntimeError(
        "ServiceVerifier artifact not found"
    )


with open(
    ESCROW_ARTIFACT,
    "r",
    encoding="utf-8"
) as file:
    escrow_abi = json.load(file)["abi"]


with open(
    VERIFIER_ARTIFACT,
    "r",
    encoding="utf-8"
) as file:
    verifier_abi = json.load(file)["abi"]


# =========================================================
# CONTRACT OBJECTS
# =========================================================

escrow = w3.eth.contract(
    address=Web3.to_checksum_address(
        ESCROW_ADDRESS
    ),
    abi=escrow_abi
)

verifier = w3.eth.contract(
    address=Web3.to_checksum_address(
        SERVICE_VERIFIER_ADDRESS
    ),
    abi=verifier_abi
)


# =========================================================
# READ ESCROW
# =========================================================

def get_escrow(escrow_id):
    """
    Read the requested escrow directly from
    the deployed blockchain contract.
    """

    return escrow.functions.getEscrow(
        int(escrow_id)
    ).call()


# =========================================================
# BUILD REQUEST HASH
# =========================================================

def create_request_hash(service_request):
    """
    Create the same deterministic request hash
    used during escrow creation.
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

    return request_hash, canonical_json


# =========================================================
# VALIDATE SERVICE RESULT
# =========================================================

def validate_service_result(
    service_request,
    service_result
):
    """
    Determine whether the real service result is
    consistent with the runtime request.

    No fixed valid=True / valid=False value is used.
    """

    checks = {}

    # -----------------------------------------------------
    # Request coordinates
    # -----------------------------------------------------

    requested_latitude = service_request.get(
        "latitude"
    )

    requested_longitude = service_request.get(
        "longitude"
    )

    returned_latitude = service_result.get(
        "latitude"
    )

    returned_longitude = service_result.get(
        "longitude"
    )

    checks["latitude_matches"] = (
        requested_latitude is not None
        and returned_latitude is not None
        and float(requested_latitude)
        == float(returned_latitude)
    )

    checks["longitude_matches"] = (
        requested_longitude is not None
        and returned_longitude is not None
        and float(requested_longitude)
        == float(returned_longitude)
    )


    # -----------------------------------------------------
    # Service source
    # -----------------------------------------------------

    checks["source_present"] = bool(
        service_result.get("source")
    )


    # -----------------------------------------------------
    # Observation timestamp
    # -----------------------------------------------------

    checks["observed_at_present"] = bool(
        service_result.get("observed_at")
    )


    # -----------------------------------------------------
    # Weather data fields
    # -----------------------------------------------------

    weather_fields = [
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "weather_code"
    ]

    checks["weather_data_present"] = all(
        service_result.get(field) is not None
        for field in weather_fields
    )


    # -----------------------------------------------------
    # Final decision
    # -----------------------------------------------------

    valid = all(
        checks.values()
    )

    return {
        "valid": valid,
        "checks": checks
    }


# =========================================================
# PREPARE VERIFICATION
# =========================================================

def prepare_verification(
    escrow_id,
    service_request,
    service_result
):
    """
    Read actual escrow state and prepare a
    dynamically computed verification decision.
    """

    on_chain = get_escrow(
        escrow_id
    )

    on_chain_provider = on_chain[1]
    on_chain_agent_id = on_chain[2]
    on_chain_request_hash = on_chain[4]
    on_chain_status = on_chain[7]


    # -----------------------------------------------------
    # Calculate request hash from runtime request
    # -----------------------------------------------------

    request_hash, canonical_request = (
        create_request_hash(
            service_request
        )
    )


    # -----------------------------------------------------
    # Check request integrity
    # -----------------------------------------------------

    request_hash_matches = (
        on_chain_request_hash.hex()
        == request_hash.hex()
    )


    # -----------------------------------------------------
    # Calculate actual service result hash
    # -----------------------------------------------------

    canonical_result = json.dumps(
        service_result,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    )

    result_hash = Web3.keccak(
        text=canonical_result
    )


    # -----------------------------------------------------
    # Validate service result
    # -----------------------------------------------------

    result_validation = validate_service_result(
        service_request,
        service_result
    )


    # -----------------------------------------------------
    # Final verification decision
    # -----------------------------------------------------

    valid = (
        request_hash_matches
        and result_validation["valid"]
    )


    return {
        "escrow_id": int(escrow_id),
        "provider": on_chain_provider,
        "agent_id": on_chain_agent_id,
        "escrow_status": on_chain_status,
        "request_hash": request_hash.hex(),
        "canonical_request": canonical_request,
        "result_hash": result_hash.hex(),
        "canonical_result": canonical_result,
        "request_hash_matches": request_hash_matches,
        "validation_checks": result_validation["checks"],
        "valid": valid
    }


# =========================================================
# SEND CREATE VERIFICATION TRANSACTION
# =========================================================

def create_verification_record(
    escrow_id,
    prepared
):
    """
    Create a verification record on the deployed
    ServiceVerifier contract.
    """

    function_call = verifier.functions.createVerification(
        int(escrow_id),
        Web3.to_checksum_address(
            prepared["provider"]
        ),
        bytes.fromhex(
            prepared["request_hash"]
        )
    )


    estimated_gas = function_call.estimate_gas({
        "from": WALLET_ADDRESS
    })

    gas_limit = int(
        estimated_gas * 1.20
    )

    nonce = w3.eth.get_transaction_count(
        WALLET_ADDRESS,
        "pending"
    )

    gas_price = w3.eth.gas_price

    transaction = function_call.build_transaction({
        "from": WALLET_ADDRESS,
        "nonce": nonce,
        "chainId": w3.eth.chain_id,
        "gas": gas_limit,
        "gasPrice": gas_price
    })

    signed = account.sign_transaction(
        transaction
    )

    tx_hash = w3.eth.send_raw_transaction(
        signed.raw_transaction
    )

    receipt = w3.eth.wait_for_transaction_receipt(
        tx_hash
    )

    if receipt.status != 1:
        raise RuntimeError(
            "createVerification transaction failed"
        )

    return {
        "success": True,
        "transaction_hash": tx_hash.hex(),
        "block_number": receipt.blockNumber,
        "gas_used": receipt.gasUsed
    }


# =========================================================
# VERIFY SERVICE ON BLOCKCHAIN
# =========================================================

def verify_service(
    escrow_id,
    prepared
):
    """
    Submit the dynamically calculated verification
    result to the deployed ServiceVerifier contract.
    """

    function_call = verifier.functions.verifyService(
        int(escrow_id),
        bytes.fromhex(
            prepared["result_hash"]
        ),
        bool(
            prepared["valid"]
        )
    )


    estimated_gas = function_call.estimate_gas({
        "from": WALLET_ADDRESS
    })

    gas_limit = int(
        estimated_gas * 1.20
    )

    nonce = w3.eth.get_transaction_count(
        WALLET_ADDRESS,
        "pending"
    )

    gas_price = w3.eth.gas_price

    transaction = function_call.build_transaction({
        "from": WALLET_ADDRESS,
        "nonce": nonce,
        "chainId": w3.eth.chain_id,
        "gas": gas_limit,
        "gasPrice": gas_price
    })

    signed = account.sign_transaction(
        transaction
    )

    tx_hash = w3.eth.send_raw_transaction(
        signed.raw_transaction
    )

    receipt = w3.eth.wait_for_transaction_receipt(
        tx_hash
    )

    if receipt.status != 1:
        raise RuntimeError(
            "verifyService transaction failed"
        )

    return {
        "success": True,
        "valid": prepared["valid"],
        "transaction_hash": tx_hash.hex(),
        "block_number": receipt.blockNumber,
        "gas_used": receipt.gasUsed
    }


# =========================================================
# READ VERIFICATION
# =========================================================

def get_verification(
    escrow_id
):
    """
    Read the verification record directly from
    the deployed ServiceVerifier contract.
    """

    return verifier.functions.getVerification(
        int(escrow_id)
    ).call()