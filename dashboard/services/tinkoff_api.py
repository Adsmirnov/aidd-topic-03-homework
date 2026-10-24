from datetime import datetime

import requests

from config.settings import TINKOFF_API_BASE_URL, TINKOFF_TOKEN


def post(endpoint, payload):
    if not TINKOFF_TOKEN:
        raise RuntimeError("TINKOFF_TOKEN is not configured")

    response = requests.post(
        f"{TINKOFF_API_BASE_URL}/{endpoint}",
        headers={"Authorization": f"Bearer {TINKOFF_TOKEN}"},
        json=payload,
        timeout=(5, 30),
    )
    response.raise_for_status()
    return response.json()


def quotation_to_float(quotation):
    return float(quotation.get("units", 0)) + int(quotation.get("nano", 0)) / 1_000_000_000


def parse_api_datetime(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
