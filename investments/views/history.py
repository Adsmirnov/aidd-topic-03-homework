from django.shortcuts import get_object_or_404, render

from dashboard.models import Share
from investments.charts import line_chart
from investments.forms import HistoryPeriodForm
from investments.services.history import get_history, period_bounds, period_stats


def share_history(request, pk):
    """История цен акции за выбранный период"""
    share = get_object_or_404(Share, pk=pk)
    form = HistoryPeriodForm(request.GET or None)
    params = form.cleaned_data if form.is_valid() else {}
    start, end = period_bounds(
        params.get("period"), params.get("date_from"), params.get("date_to")
    )
    records, baseline = get_history(share, start, end)
    stats = period_stats(records, baseline)
    chart = None
    if records:
        chart = line_chart(
            [r.recorded_at for r in records], [r.price for r in records], share.ticker, step=True
        )
    return render(
        request,
        "investments/history.html",
        {
            "share": share,
            "form": form,
            "records": records[::-1],
            "stats": stats,
            "chart": chart,
            "start": start,
            "end": end,
        },
    )
