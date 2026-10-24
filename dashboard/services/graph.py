from datetime import timedelta

from plotly.graph_objs import Scatter
from plotly.offline import plot
from tinkoff.invest import CandleInterval, Client
from tinkoff.invest.utils import now, quotation_to_decimal

from config.settings import TINKOFF_TOKEN, logger


def get_graph(share):
    """Return a Plotly chart (HTML div) of daily close prices, or None on API errors."""
    try:
        with Client(TINKOFF_TOKEN) as client:
            x_data, y_data = [], []
            for candle in client.get_all_candles(
                figi=share.figi,
                from_=now() - timedelta(days=180),
                interval=CandleInterval.CANDLE_INTERVAL_DAY,
            ):
                x_data.append(candle.time.date())
                y_data.append(float(quotation_to_decimal(candle.close)))
    except Exception as e:
        logger.error(f"Failed to get candles for share with id {share.id}: {e}")
        return None

    plot_div = plot(
        [
            Scatter(
                x=x_data,
                y=y_data,
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
    return plot_div
