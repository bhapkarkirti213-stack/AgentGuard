import json
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from web3 import Web3


# =========================================================
# OPEN-METEO WEATHER SERVICE
# =========================================================

OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
)


# =========================================================
# FETCH REAL WEATHER DATA
# =========================================================

def fetch_weather(
    latitude,
    longitude
):
    """
    Fetch live weather data from Open-Meteo.

    Latitude and longitude are supplied at runtime.
    No location is hardcoded.
    """

    latitude = float(latitude)
    longitude = float(longitude)

    if not -90 <= latitude <= 90:
        raise ValueError(
            "Latitude must be between -90 and 90"
        )

    if not -180 <= longitude <= 180:
        raise ValueError(
            "Longitude must be between -180 and 180"
        )

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "wind_speed_10m,"
            "weather_code"
        ),
        "timezone": "UTC"
    }

    url = (
        OPEN_METEO_URL
        + "?"
        + urlencode(params)
    )

    request = Request(
        url,
        headers={
            "User-Agent":
                "AgentGuard/1.0"
        }
    )

    with urlopen(
        request,
        timeout=20
    ) as response:

        if response.status != 200:
            raise RuntimeError(
                f"Weather service returned HTTP {response.status}"
            )

        raw_data = response.read()

    data = json.loads(
        raw_data.decode("utf-8")
    )

    if "current" not in data:
        raise RuntimeError(
            "Weather response does not contain current data"
        )

    current = data["current"]
    units = data.get(
        "current_units",
        {}
    )

    # -----------------------------------------------------
    # Use values returned by the real service
    # -----------------------------------------------------

    result = {
        "source": "Open-Meteo",
        "latitude": latitude,
        "longitude": longitude,
        "timezone": data.get(
            "timezone"
        ),
        "observed_at": current.get(
            "time"
        ),
        "temperature_2m": current.get(
            "temperature_2m"
        ),
        "temperature_unit": units.get(
            "temperature_2m"
        ),
        "relative_humidity_2m": current.get(
            "relative_humidity_2m"
        ),
        "humidity_unit": units.get(
            "relative_humidity_2m"
        ),
        "wind_speed_10m": current.get(
            "wind_speed_10m"
        ),
        "wind_speed_unit": units.get(
            "wind_speed_10m"
        ),
        "weather_code": current.get(
            "weather_code"
        ),
        "retrieved_at": datetime.now(
            timezone.utc
        ).isoformat()
    }

    return result


# =========================================================
# CANONICAL SERVICE RESULT
# =========================================================

def canonicalize_result(result):
    """
    Convert service result into deterministic JSON.
    """

    return json.dumps(
        result,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    )


# =========================================================
# HASH SERVICE RESULT
# =========================================================

def hash_service_result(result):
    """
    Generate a cryptographic hash of the actual
    service result.
    """

    canonical_json = canonicalize_result(
        result
    )

    result_hash = Web3.keccak(
        text=canonical_json
    )

    return result_hash, canonical_json


# =========================================================
# COMPLETE SERVICE CALL
# =========================================================

def execute_weather_service(
    latitude,
    longitude
):
    """
    Fetch real weather data and produce its
    cryptographic evidence.
    """

    result = fetch_weather(
        latitude,
        longitude
    )

    result_hash, canonical_json = (
        hash_service_result(
            result
        )
    )

    return {
        "service_result": result,
        "canonical_result": canonical_json,
        "result_hash": result_hash.hex()
    }