from django.urls import path

from investments.views import history

app_name = "investments"

urlpatterns = [
    path("history/<int:pk>/", history.share_history, name="history"),
]
