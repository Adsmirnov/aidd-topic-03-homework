from plotly.graph_objs import Scatter
from plotly.offline import plot


def line_chart(dates, values, name, step=False):
    """Plotly line chart as an HTML div (Plotly JS is loaded from the CDN)."""
    return plot(
        [
            Scatter(
                x=dates,
                y=[float(v) for v in values],
                mode="lines+markers" if len(values) < 50 else "lines",
                name=name,
                line_shape="hv" if step else "linear",
            )
        ],
        output_type="div",
        include_plotlyjs="cdn",
        config={"displaylogo": False},
    )
