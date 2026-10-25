import logging

from .tinkoff import quotation_to_decimal, tinkoff_client

logger = logging.getLogger("main")

# T-Invest API accepts up to 3000 instruments in one GetLastPrices request
LAST_PRICES_BATCH_SIZE = 1000


def get_last_prices(figis):
    """Return {figi: price} for the given FIGIs, requesting them in batches."""
    prices = {}
    with tinkoff_client() as client:
        for start in range(0, len(figis), LAST_PRICES_BATCH_SIZE):
            batch = figis[start : start + LAST_PRICES_BATCH_SIZE]
            resp = client.market_data.get_last_prices(figi=batch)
            for last_price in resp.last_prices:
                price = float(quotation_to_decimal(last_price.price))
                # Instruments without trades (e.g. delisted) come back with price 0
                # and time 1970-01-01: that means "no price", not a price of zero
                if price > 0:
                    prices[last_price.figi] = price
    logger.info(f"Got last prices for {len(prices)} of {len(figis)} shares")
    return prices
