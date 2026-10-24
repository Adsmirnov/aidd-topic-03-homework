from django.urls import path

from dashboard.history_views import price_history

app_name = "history"

urlpatterns = [path("", price_history, name="index")]
