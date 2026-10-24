from django.urls import include, path

from dashboard.views import (
    ShareCreateView,
    ShareDeleteView,
    ShareDetailView,
    ShareListView,
    ShareUpdateView,
)

app_name = "dashboard"

urlpatterns = [
    path("", ShareListView.as_view(), name="index"),
    path("<int:pk>", ShareDetailView.as_view(), name="detail"),
    path("create", ShareCreateView.as_view(), name="create"),
    path("update/<int:pk>", ShareUpdateView.as_view(), name="update"),
    path("delete/<int:pk>", ShareDeleteView.as_view(), name="delete"),
    path("monitoring/", include("dashboard.monitoring_urls")),
    path("portfolios/", include("dashboard.portfolio_urls")),
    path("history/", include("dashboard.history_urls")),
    path("strategies/", include("dashboard.strategy_urls")),
    path("api/", include("dashboard.api.urls")),
]
