from datetime import datetime, timedelta, timezone

from plotly.graph_objs import Scatter
from plotly.offline import plot

from .tinkoff_api import parse_api_datetime, post, quotation_to_float


def get_graph(share):
    end_time = datetime.now(timezone.utc)
    response = post(
        "MarketDataService/GetCandles",
        {
            "instrumentId": share.figi,
            "from": (end_time - timedelta(days=180)).isoformat(),
            "to": end_time.isoformat(),
            "interval": "CANDLE_INTERVAL_DAY",
        },
    )
    candles = response.get("candles", [])
    x_data = [
        parse_api_datetime(candle["time"]).date() for candle in candles
    ]
    y_data = [quotation_to_float(candle["close"]) for candle in candles]

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
    )
    return plot_div
