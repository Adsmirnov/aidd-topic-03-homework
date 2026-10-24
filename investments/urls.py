from django.urls import path

from investments.views import history, portfolios, watchlists

app_name = "investments"

urlpatterns = [
    path("history/<int:pk>/", history.share_history, name="history"),
    path("watchlists/", watchlists.watchlist_list, name="watchlists"),
    path("watchlists/<int:pk>/", watchlists.watchlist_detail, name="watchlist"),
    path("watchlists/<int:pk>/rename/", watchlists.watchlist_rename, name="watchlist_rename"),
    path("watchlists/<int:pk>/delete/", watchlists.watchlist_delete, name="watchlist_delete"),
    path("watchlists/items/<int:pk>/delete/", watchlists.item_delete, name="item_delete"),
    path("watchlists/items/<int:item_pk>/alerts/", watchlists.alert_create, name="alert_create"),
    path("alerts/<int:pk>/delete/", watchlists.alert_delete, name="alert_delete"),
    path("alerts/<int:pk>/rearm/", watchlists.alert_rearm, name="alert_rearm"),
    path("notifications/", watchlists.notification_list, name="notifications"),
    path("notifications/read/", watchlists.notifications_read, name="notifications_read"),
    path("portfolios/", portfolios.portfolio_list, name="portfolios"),
    path("portfolios/<int:pk>/", portfolios.portfolio_detail, name="portfolio"),
    path("portfolios/<int:pk>/rename/", portfolios.portfolio_rename, name="portfolio_rename"),
    path("portfolios/<int:pk>/delete/", portfolios.portfolio_delete, name="portfolio_delete"),
]
