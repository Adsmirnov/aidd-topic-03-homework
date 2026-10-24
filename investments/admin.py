from django.contrib import admin

from investments.models import Notification, PriceAlert, SharePrice, Watchlist


@admin.register(SharePrice)
class SharePriceAdmin(admin.ModelAdmin):
    list_display = ("share", "price", "recorded_at")
    list_filter = ("share",)
    date_hierarchy = "recorded_at"


@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "created_at")


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = ("item", "condition", "target_price", "triggered_at")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("message", "user", "triggered_at", "read_at")
