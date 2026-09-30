import json

import joblib
import pandas as pd

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from feature_service import get_blockchain_features


# ==========================================
# Load ML model
# ==========================================

try:

    model = joblib.load(
        "logistic_risk_model.pkl"
    )

    scaler = joblib.load(
        "risk_scaler.pkl"
    )

    with open(
        "feature_columns.json",
        "r",
        encoding="utf-8"
    ) as file:

        feature_columns = json.load(file)

except Exception as error:

    raise RuntimeError(
        f"Could not load ML artifacts: {error}"
    )


# ==========================================
# FastAPI
# ==========================================

app = FastAPI(
    title="AgentGuard Risk Engine",
    description=(
        "Blockchain-backed ML transaction risk "
        "assessment service"
    ),
    version="2.0.0"
)


# ==========================================
# Request model
# ==========================================

class RiskRequest(BaseModel):

    agent_id: str

    transaction_amount: float


# ==========================================
# Health
# ==========================================

@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "AgentGuard Risk Engine",
        "version": "2.0.0"
    }


# ==========================================
# Risk assessment
# ==========================================

@app.post("/assess")
def assess_risk(request: RiskRequest):

    if request.transaction_amount <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "Transaction amount must be "
                "greater than 0"
            )
        )


    try:

        # --------------------------------------
        # Get fresh blockchain data
        # --------------------------------------

        blockchain_data = get_blockchain_features(

            request.agent_id,

            request.transaction_amount
        )


        transaction = blockchain_data[
            "features"
        ]


        # --------------------------------------
        # Prepare ML input
        # --------------------------------------

        input_data = pd.DataFrame(

            [transaction],

            columns=feature_columns
        )


        scaled_input = scaler.transform(
            input_data
        )


        # --------------------------------------
        # Prediction
        # --------------------------------------

        risk_probability = model.predict_proba(

            scaled_input

        )[0][1]


        risk_score = (
            risk_probability * 100
        )


        # --------------------------------------
        # AgentGuard policy
        # --------------------------------------

        if risk_probability < 0.30:

            risk_level = "LOW"
            decision = "AUTO_APPROVE"

        elif risk_probability < 0.70:

            risk_level = "MEDIUM"
            decision = "EXTRA_CHECKS"

        else:

            risk_level = "HIGH"
            decision = "HUMAN_APPROVAL"


        # --------------------------------------
        # Response
        # --------------------------------------

        return {

            "network": "Ethereum Sepolia",

            "chain_id": 11155111,

            "agent_id":
                blockchain_data["agent_id"],

            "provider":
                blockchain_data["provider"],

            "service_type":
                blockchain_data["service_type"],

            "active":
                blockchain_data["active"],

            "transaction_amount":
                request.transaction_amount,

            "reputation_score":
                transaction[
                    "reputation_score"
                ],

            "successful_transactions":
                transaction[
                    "successful_transactions"
                ],

            "failed_transactions":
                transaction[
                    "failed_transactions"
                ],

            "refunded_transactions":
                transaction[
                    "refunded_transactions"
                ],

            "disputes":
                transaction[
                    "disputes"
                ],

            "agent_age_days":
                transaction[
                    "agent_age_days"
                ],

            "amount_vs_history":
                transaction[
                    "amount_vs_history"
                ],

            "risk_probability":
                round(
                    risk_probability,
                    4
                ),

            "risk_score":
                round(
                    risk_score,
                    2
                ),

            "risk_level":
                risk_level,

            "decision":
                decision
        }


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