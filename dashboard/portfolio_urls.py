from django.urls import path

from dashboard.portfolio_views import create_portfolio, portfolios, record_transaction

app_name = "portfolios"

urlpatterns = [
    path("", portfolios, name="list"),
    path("create/", create_portfolio, name="create"),
    path("<int:portfolio_id>/transactions/", record_transaction, name="transaction"),
]
