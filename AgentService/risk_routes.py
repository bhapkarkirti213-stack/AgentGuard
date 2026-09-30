from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from risk_client import assess_transaction_risk


router = APIRouter(
    prefix="/risk",
    tags=["Risk Engine"]
)


class RiskAssessmentRequest(BaseModel):
    agent_id: str
    transaction_amount: float


@router.post("/assess")
def assess_risk(request: RiskAssessmentRequest):

    if request.transaction_amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Transaction amount must be greater than 0"
        )

    try:

        result = assess_transaction_risk(
            request.agent_id,
            request.transaction_amount
        )

        return {
            "success": True,
            "risk_assessment": result
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