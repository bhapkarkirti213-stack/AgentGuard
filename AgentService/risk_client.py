import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


RISK_ENGINE_URL = "http://127.0.0.1:8001/assess"


def assess_transaction_risk(agent_id, transaction_amount):
    """
    Send an AgentGuard transaction request
    to the local ML Risk Engine.
    """

    payload = {
        "agent_id": agent_id,
        "transaction_amount": transaction_amount
    }

    data = json.dumps(payload).encode("utf-8")

    request = Request(
        RISK_ENGINE_URL,
        data=data,
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:

        with urlopen(request, timeout=30) as response:

            response_data = response.read().decode(
                "utf-8"
            )

            return json.loads(response_data)

    except HTTPError as error:

        body = error.read().decode(
            "utf-8"
        )

        raise RuntimeError(
            f"Risk Engine returned HTTP "
            f"{error.code}: {body}"
        )

    except URLError as error:

        raise RuntimeError(
            f"Could not connect to Risk Engine: "
            f"{error.reason}"
        )