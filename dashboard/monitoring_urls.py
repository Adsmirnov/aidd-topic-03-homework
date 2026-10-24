from django.urls import path

from dashboard.monitoring_views import (
    add_price_alert,
    add_watchlist_entry,
    create_watchlist,
    delete_watchlist_entry,
    mark_notification_read,
    monitoring,
)

app_name = "monitoring"

urlpatterns = [
    path("", monitoring, name="index"),
    path("watchlists/create/", create_watchlist, name="create-watchlist"),
    path("watchlists/<int:watchlist_id>/entries/", add_watchlist_entry, name="add-entry"),
    path("entries/<int:entry_id>/alerts/", add_price_alert, name="add-alert"),
    path("entries/<int:entry_id>/delete/", delete_watchlist_entry, name="delete-entry"),
    path("notifications/<int:notification_id>/read/", mark_notification_read, name="read-notification"),
]
