from datetime import datetime

from .tinkoff_api import post, quotation_to_float


def get_last_data(share):
    response = post("MarketDataService/GetLastPrices", {"instrumentId": [share.figi]})
    last_prices = response.get("lastPrices", [])
    if not last_prices:
        raise ValueError(f"No last price returned for FIGI {share.figi}")

    last_price = last_prices[-1]
    timestamp = datetime.fromisoformat(last_price["time"].replace("Z", "+00:00"))
    return quotation_to_float(last_price["price"]), timestamp
