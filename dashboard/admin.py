from django.contrib import admin

from dashboard.models import Share


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ("figi", "isin", "name", "ticker", "class_code", "currency")
    search_fields = ("figi", "isin", "name", "ticker")
    fields = (
        "figi",
        "isin",
        "name",
        "ticker",
        "class_code",
        "currency",
        "uid",
        "last_price",
        "is_trend_high",
    )
