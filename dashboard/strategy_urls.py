from django.urls import path

from dashboard.strategy_views import create_strategy, strategies, toggle_strategy

app_name = "strategies"

urlpatterns = [
    path("", strategies, name="index"),
    path("create/", create_strategy, name="create"),
    path("<int:strategy_id>/toggle/", toggle_strategy, name="toggle"),
]
