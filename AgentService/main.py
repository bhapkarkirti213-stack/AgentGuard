import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

# --------------------------------------------------
# Environment variables
# --------------------------------------------------

RPC_URL = os.getenv("SEPOLIA_RPC_URL")
REGISTRY_ADDRESS = os.getenv("AGENT_REGISTRY_ADDRESS")
AGENT_PRIVATE_KEY = os.getenv("AGENT_PRIVATE_KEY")

if not RPC_URL:
    raise RuntimeError("SEPOLIA_RPC_URL is missing")

if not REGISTRY_ADDRESS:
    raise RuntimeError("AGENT_REGISTRY_ADDRESS is missing")

if not AGENT_PRIVATE_KEY:
    raise RuntimeError("AGENT_PRIVATE_KEY is missing")


# --------------------------------------------------
# Connect to Ethereum Sepolia
# --------------------------------------------------

w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    raise RuntimeError("Could not connect to Ethereum Sepolia")

chain_id = w3.eth.chain_id

if chain_id != 11155111:
    raise RuntimeError(
        f"Wrong network. Expected Sepolia 11155111, got {chain_id}"
    )


# --------------------------------------------------
# Load AgentRegistry ABI
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ABI_PATH = (
    PROJECT_ROOT
    / "Blockchain"
    / "artifacts"
    / "contracts"
    / "AgentRegistry.sol"
    / "AgentRegistry.json"
)

if not ABI_PATH.exists():
    raise RuntimeError(
        f"AgentRegistry artifact not found: {ABI_PATH}"
    )

with open(ABI_PATH, "r", encoding="utf-8") as file:
    artifact = json.load(file)

ABI = artifact["abi"]


# --------------------------------------------------
# Smart contract
# --------------------------------------------------

registry = w3.eth.contract(
    address=Web3.to_checksum_address(REGISTRY_ADDRESS),
    abi=ABI
)


# --------------------------------------------------
# Agent wallet
# --------------------------------------------------

account = w3.eth.account.from_key(AGENT_PRIVATE_KEY)

AGENT_WALLET = account.address


# --------------------------------------------------
# FastAPI application
# --------------------------------------------------

app = FastAPI(
    title="AgentGuard Agent Registration Service",
    version="1.0.0"
)


# --------------------------------------------------
# Request model
# --------------------------------------------------

class AgentRegistration(BaseModel):

    agent_id: str = Field(
        min_length=3,
        max_length=100
    )

    service_type: str = Field(
        min_length=2,
        max_length=100
    )


# --------------------------------------------------
# Root endpoint
# --------------------------------------------------

@app.get("/")
def root():

    return {
        "project": "AgentGuard",
        "service": "Agent Registration Service",
        "status": "running",
        "network": "Ethereum Sepolia",
        "chain_id": chain_id
    }


# --------------------------------------------------
# Blockchain status
# --------------------------------------------------

@app.get("/blockchain/status")
def blockchain_status():

    balance = w3.from_wei(
        w3.eth.get_balance(AGENT_WALLET),
        "ether"
    )

    return {
        "connected": w3.is_connected(),
        "network": "Ethereum Sepolia",
        "chain_id": chain_id,
        "agent_wallet": AGENT_WALLET,
        "balance_eth": str(balance),
        "registry_contract": REGISTRY_ADDRESS
    }

# --------------------------------------------------
# Agent lookup / discovery
# --------------------------------------------------

@app.get("/agents/{agent_id}")
def get_agent(agent_id: str):

    try:

        # Read agent directly from AgentRegistry on Sepolia
        agent = registry.functions.getAgent(
            agent_id
        ).call()

        # Check whether agent exists
        if agent[1] == "0x0000000000000000000000000000000000000000":

            raise HTTPException(
                status_code=404,
                detail="Agent not found on blockchain"
            )

        return {
            "status": "found",
            "source": "Ethereum Sepolia",
            "agent": {
                "agent_id": agent[0],
                "wallet_address": agent[1],
                "service_type": agent[2],
                "active": agent[3],
                "registered_at": agent[4]
            },
            "registry_contract": REGISTRY_ADDRESS
        }

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )
# --------------------------------------------------
# Register agent on blockchain
# --------------------------------------------------

@app.post("/agents/register")
def register_agent(agent: AgentRegistration):

    try:

        # Check whether agent already exists
        existing_agent = registry.functions.getAgent(
            agent.agent_id
        ).call()

        existing_wallet = existing_agent[1]

        if existing_wallet != "0x0000000000000000000000000000000000000000":

            raise HTTPException(
                status_code=409,
                detail="Agent is already registered"
            )


        # Get wallet nonce
        nonce = w3.eth.get_transaction_count(
            AGENT_WALLET
        )


        # Build blockchain transaction
        transaction = registry.functions.registerAgent(
            agent.agent_id,
            agent.service_type
        ).build_transaction({

            "from": AGENT_WALLET,

            "nonce": nonce,

            "chainId": 11155111,

            "gas": 300000,

            "gasPrice": w3.eth.gas_price
        })


        # Sign transaction
        signed_transaction = w3.eth.account.sign_transaction(
            transaction,
            AGENT_PRIVATE_KEY
        )


        # Send transaction to Sepolia
        tx_hash = w3.eth.send_raw_transaction(
            signed_transaction.raw_transaction
        )


        # Wait for blockchain confirmation
        receipt = w3.eth.wait_for_transaction_receipt(
            tx_hash
        )


        # Read agent from blockchain
        registered_agent = registry.functions.getAgent(
            agent.agent_id
        ).call()


        return {

            "status": "registered",

            "agent": {

                "agent_id": registered_agent[0],

                "wallet_address": registered_agent[1],

                "service_type": registered_agent[2],

                "active": registered_agent[3],

                "registered_at": registered_agent[4]
            },

            "blockchain": {

                "network": "Ethereum Sepolia",

                "chain_id": chain_id,

                "transaction_hash": tx_hash.hex(),

                "block_number": receipt["blockNumber"],

                "contract_address": REGISTRY_ADDRESS
            }
        }


    except HTTPException:

        raise


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )