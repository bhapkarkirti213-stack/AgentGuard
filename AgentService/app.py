import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from eth_account import Account
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from web3 import Web3

from risk_client import assess_transaction_risk
from risk_routes import router as risk_router
from escrow_service import create_escrow


# =========================================================
# PROJECT PATHS
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

if not RPC_URL:
    raise RuntimeError(
        "SEPOLIA_RPC_URL is missing from environment"
    )

if not PRIVATE_KEY:
    raise RuntimeError(
        "SEPOLIA_PRIVATE_KEY is missing from environment"
    )


# =========================================================
# WEB3 / SEPOLIA CONNECTION
# =========================================================

w3 = Web3(
    Web3.HTTPProvider(
        RPC_URL,
        request_kwargs={
            "timeout": 20
        }
    )
)

if w3.is_connected():
    CHAIN_ID = w3.eth.chain_id
else:
    CHAIN_ID = None


if CHAIN_ID is not None and CHAIN_ID != 11155111:
    raise RuntimeError(
        f"Wrong network. Expected Sepolia "
        f"(11155111), got {CHAIN_ID}"
    )


# =========================================================
# AGENT WALLET
# =========================================================

account = Account.from_key(PRIVATE_KEY)

AGENT_WALLET = account.address


# =========================================================
# AGENT REGISTRY
# =========================================================

REGISTRY_ADDRESS = (
    "0xD19597a1fD327B16CbCEEb8e22D5b299AAFBe6fE"
)

REGISTRY_ARTIFACT = (
    BLOCKCHAIN_DIR
    / "artifacts"
    / "contracts"
    / "AgentRegistry.sol"
    / "AgentRegistry.json"
)


if not REGISTRY_ARTIFACT.exists():
    raise RuntimeError(
        "AgentRegistry artifact not found: "
        f"{REGISTRY_ARTIFACT}"
    )


with open(
    REGISTRY_ARTIFACT,
    "r",
    encoding="utf-8"
) as file:
    registry_artifact = json.load(file)


registry = w3.eth.contract(
    address=Web3.to_checksum_address(
        REGISTRY_ADDRESS
    ),
    abi=registry_artifact["abi"]
)


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="AgentGuard Agent Service",
    description=(
        "AgentGuard agent service with Ethereum Sepolia "
        "integration, ML risk assessment, and "
        "risk-gated escrow execution"
    ),
    version="2.0.0"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


# =========================================================
# RISK ENGINE ROUTER
# =========================================================

app.include_router(risk_router)


# =========================================================
# REQUEST MODELS
# =========================================================

class AgentRegistrationRequest(BaseModel):
    agent_id: str
    service_type: str


class TransactionPreflightRequest(BaseModel):
    agent_id: str
    transaction_amount: float


class TransactionExecutionRequest(BaseModel):
    agent_id: str
    transaction_amount: float
    service_request: dict
    deadline: int | None = None


# =========================================================
# AUTONOMOUS SPENDING LIMIT
# =========================================================

# Experimental development policy.
# Transactions above this limit cannot be
# automatically executed even if the ML model
# classifies them as low risk.
MAX_AUTONOMOUS_ESCROW_ETH = 0.01


# =========================================================
# HELPER: REQUIRE BLOCKCHAIN CONNECTION
# =========================================================

def require_blockchain_connection():
    """
    Make sure AgentService currently has a working
    connection to Ethereum Sepolia.
    """

    if not w3.is_connected():
        raise HTTPException(
            status_code=503,
            detail=(
                "AgentService cannot currently connect "
                "to Ethereum Sepolia RPC"
            )
        )

    if w3.eth.chain_id != 11155111:
        raise HTTPException(
            status_code=503,
            detail=(
                "Connected blockchain is not Ethereum Sepolia"
            )
        )


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():

    return {
        "service": "AgentGuard Agent Service",
        "status": "running",
        "network": "Ethereum Sepolia",
        "chain_id": CHAIN_ID,
        "wallet": AGENT_WALLET
    }


# =========================================================
# BLOCKCHAIN STATUS
# =========================================================

@app.get("/blockchain/status")
def blockchain_status():

    require_blockchain_connection()

    try:

        balance_wei = w3.eth.get_balance(
            AGENT_WALLET
        )

        balance_eth = float(
            w3.from_wei(
                balance_wei,
                "ether"
            )
        )

        return {
            "connected": True,
            "network": "Ethereum Sepolia",
            "chain_id": 11155111,
            "wallet": AGENT_WALLET,
            "balance_eth": balance_eth,
            "registry": REGISTRY_ADDRESS
        }

    except Exception as error:

        raise HTTPException(
            status_code=503,
            detail=str(error)
        )


# =========================================================
# GET AGENT
# =========================================================

@app.get("/agents/{agent_id}")
def get_agent(agent_id: str):

    require_blockchain_connection()

    try:

        agent = registry.functions.getAgent(
            agent_id
        ).call()

        wallet = agent[1]

        zero_address = (
            "0x0000000000000000000000000000000000000000"
        )

        if wallet == zero_address:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"Agent '{agent_id}' not registered"
                )
            )

        registered_at = agent[4]

        return {
            "agent_id": agent[0],
            "wallet": wallet,
            "service_type": agent[2],
            "active": agent[3],
            "registered_at": registered_at,
            "registered_at_utc": (
                datetime.fromtimestamp(
                    registered_at,
                    timezone.utc
                ).isoformat()
            )
        }

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=503,
            detail=str(error)
        )


# =========================================================
# REGISTER AGENT
# =========================================================

@app.post("/agents/register")
def register_agent(
    request: AgentRegistrationRequest
):

    require_blockchain_connection()

    agent_id = request.agent_id.strip()
    service_type = request.service_type.strip()

    if not agent_id:

        raise HTTPException(
            status_code=400,
            detail="agent_id cannot be empty"
        )

    if not service_type:

        raise HTTPException(
            status_code=400,
            detail="service_type cannot be empty"
        )

    try:

        # -------------------------------------------------
        # Check existing registration
        # -------------------------------------------------

        existing = registry.functions.getAgent(
            agent_id
        ).call()

        existing_wallet = existing[1]

        zero_address = (
            "0x0000000000000000000000000000000000000000"
        )

        if existing_wallet != zero_address:

            raise HTTPException(
                status_code=409,
                detail="Agent already registered"
            )


        # -------------------------------------------------
        # Get nonce
        # -------------------------------------------------

        nonce = w3.eth.get_transaction_count(
            AGENT_WALLET,
            "pending"
        )


        # -------------------------------------------------
        # Current gas price
        # -------------------------------------------------

        gas_price = w3.eth.gas_price


        # -------------------------------------------------
        # Build transaction
        # -------------------------------------------------

        transaction = (
            registry.functions.registerAgent(
                agent_id,
                service_type
            )
            .build_transaction({

                "from": AGENT_WALLET,

                "nonce": nonce,

                "chainId": 11155111,

                "gas": 300000,

                "gasPrice": gas_price
            })
        )


        # -------------------------------------------------
        # Sign
        # -------------------------------------------------

        signed_transaction = account.sign_transaction(
            transaction
        )


        # -------------------------------------------------
        # Send
        # -------------------------------------------------

        tx_hash = w3.eth.send_raw_transaction(
            signed_transaction.raw_transaction
        )


        # -------------------------------------------------
        # Wait for confirmation
        # -------------------------------------------------

        receipt = w3.eth.wait_for_transaction_receipt(
            tx_hash
        )


        if receipt.status != 1:

            raise HTTPException(
                status_code=500,
                detail=(
                    "Agent registration transaction failed"
                )
            )


        # -------------------------------------------------
        # Read confirmed agent
        # -------------------------------------------------

        registered_agent = registry.functions.getAgent(
            agent_id
        ).call()


        return {

            "success": True,

            "agent_id":
                registered_agent[0],

            "wallet":
                registered_agent[1],

            "service_type":
                registered_agent[2],

            "active":
                registered_agent[3],

            "registered_at":
                registered_agent[4],

            "transaction_hash":
                tx_hash.hex(),

            "block_number":
                receipt.blockNumber
        }


    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# =========================================================
# TRANSACTION PREFLIGHT
# =========================================================

@app.post("/transactions/preflight")
def transaction_preflight(
    request: TransactionPreflightRequest
):

    if request.transaction_amount <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "Transaction amount must be greater than 0"
            )
        )

    try:

        # -------------------------------------------------
        # Ask ML Risk Engine
        # -------------------------------------------------

        risk = assess_transaction_risk(

            request.agent_id,

            request.transaction_amount
        )


        decision = risk["decision"]


        # -------------------------------------------------
        # Policy gate
        # -------------------------------------------------

        if decision == "AUTO_APPROVE":

            execution_allowed = True

            next_action = "CREATE_ESCROW"

        elif decision == "EXTRA_CHECKS":

            execution_allowed = False

            next_action = "EXTRA_CHECKS_REQUIRED"

        else:

            execution_allowed = False

            next_action = "HUMAN_APPROVAL_REQUIRED"


        return {

            "success": True,

            "transaction_amount":
                request.transaction_amount,

            "agent_id":
                request.agent_id,

            "risk_score":
                risk["risk_score"],

            "risk_probability":
                risk["risk_probability"],

            "risk_level":
                risk["risk_level"],

            "decision":
                decision,

            "execution_allowed":
                execution_allowed,

            "next_action":
                next_action
        }


    except RuntimeError as error:

        raise HTTPException(
            status_code=502,
            detail=str(error)
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# =========================================================
# REAL RISK-GATED ESCROW EXECUTION
# =========================================================

@app.post("/transactions/execute")
def transaction_execute(
    request: TransactionExecutionRequest
):

    if request.transaction_amount <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "Transaction amount must be greater than 0"
            )
        )


    try:

        # -------------------------------------------------
        # STEP 1: ML RISK ASSESSMENT
        # -------------------------------------------------

        risk = assess_transaction_risk(

            request.agent_id,

            request.transaction_amount
        )


        decision = risk["decision"]


        # -------------------------------------------------
        # STEP 2: ML POLICY GATE
        # -------------------------------------------------

        if decision != "AUTO_APPROVE":

            next_action = (
                "EXTRA_CHECKS_REQUIRED"
                if decision == "EXTRA_CHECKS"
                else
                "HUMAN_APPROVAL_REQUIRED"
            )

            raise HTTPException(

                status_code=403,

                detail={

                    "reason":
                        (
                            "Transaction is not eligible "
                            "for automatic execution"
                        ),

                    "agent_id":
                        request.agent_id,

                    "transaction_amount":
                        request.transaction_amount,

                    "risk_score":
                        risk["risk_score"],

                    "risk_probability":
                        risk["risk_probability"],

                    "risk_level":
                        risk["risk_level"],

                    "decision":
                        decision,

                    "next_action":
                        next_action
                }
            )


        # -------------------------------------------------
        # STEP 3: HARD SPENDING LIMIT
        # -------------------------------------------------

        if (
            request.transaction_amount
            > MAX_AUTONOMOUS_ESCROW_ETH
        ):

            raise HTTPException(

                status_code=403,

                detail={

                    "reason":
                        (
                            "Transaction exceeds "
                            "autonomous spending limit"
                        ),

                    "maximum_allowed_eth":
                        MAX_AUTONOMOUS_ESCROW_ETH,

                    "requested_eth":
                        request.transaction_amount,

                    "decision":
                        "SPENDING_LIMIT_EXCEEDED",

                    "next_action":
                        "HUMAN_APPROVAL_REQUIRED"
                }
            )


        # -------------------------------------------------
        # STEP 4: CREATE REAL SEPOLIA ESCROW
        # -------------------------------------------------

        escrow_result = create_escrow(

            request.agent_id,

            request.transaction_amount,

            request.service_request,

            request.deadline
        )


        # -------------------------------------------------
        # STEP 5: RETURN RISK + BLOCKCHAIN EVIDENCE
        # -------------------------------------------------

        return {

            "success": True,

            "execution":
                "ESCROW_CREATED",

            "risk": {

                "risk_score":
                    risk["risk_score"],

                "risk_probability":
                    risk["risk_probability"],

                "risk_level":
                    risk["risk_level"],

                "decision":
                    decision
            },

            "policy": {

                "maximum_autonomous_escrow_eth":
                    MAX_AUTONOMOUS_ESCROW_ETH,

                "execution_allowed":
                    True,

                "next_action":
                    "ESCROW_CREATED"
            },

            "blockchain":
                escrow_result
        }


    except HTTPException:
        raise

    except RuntimeError as error:

        raise HTTPException(
            status_code=502,
            detail=str(error)
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )