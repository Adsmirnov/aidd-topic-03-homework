import logging
from datetime import timedelta

from plotly.graph_objs import Scatter
from plotly.offline import plot
from tinkoff.invest import CandleInterval
from tinkoff.invest.utils import now, quotation_to_decimal

from .tinkoff import tinkoff_client

logger = logging.getLogger("main")

HISTORY_DAYS = 180


def get_close_prices(share):
    """Daily close prices for the last HISTORY_DAYS days: ([dates], [prices])."""
    dates, prices = [], []
    with tinkoff_client() as client:
        for candle in client.get_all_candles(
            figi=share.figi,
            from_=now() - timedelta(days=HISTORY_DAYS),
            interval=CandleInterval.CANDLE_INTERVAL_DAY,
        ):
            dates.append(candle.time.date())
            prices.append(float(quotation_to_decimal(candle.close)))
    return dates, prices


def get_graph(share):
    """Return a Plotly chart (HTML div) of daily close prices, or None on API errors."""
    try:
        dates, prices = get_close_prices(share)
    except Exception as e:
        logger.error(f"Failed to get candles for share with id {share.id}: {e}")
        return None

    return plot(
        [
            Scatter(
                x=dates,
                y=prices,
                mode="lines",
                name=share.ticker,
                opacity=0.8,
                marker_color="red",
            )
        ],
        output_type="div",
        include_plotlyjs="cdn",
        config={"displaylogo": False},
    )
