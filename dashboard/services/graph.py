from datetime import datetime, timedelta, timezone

from plotly.graph_objs import Scatter
from plotly.offline import plot

from .tinkoff_api import post, quotation_to_float


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
        datetime.fromisoformat(candle["time"].replace("Z", "+00:00")).date()
        for candle in candles
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
        show_link=False,
        link_text="",
    )
    return plot_div
