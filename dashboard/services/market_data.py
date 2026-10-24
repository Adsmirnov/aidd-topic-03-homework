from .tinkoff_api import parse_api_datetime, post, quotation_to_float


def get_last_data(share):
    response = post("MarketDataService/GetLastPrices", {"instrumentId": [share.figi]})
    last_prices = response.get("lastPrices", [])
    if not last_prices:
        raise ValueError(f"No last price returned for FIGI {share.figi}")

    last_price = last_prices[-1]
    timestamp = parse_api_datetime(last_price["time"])
    return quotation_to_float(last_price["price"]), timestamp
