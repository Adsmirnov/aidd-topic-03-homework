from django.contrib import admin

from investments.models import SharePrice


@admin.register(SharePrice)
class SharePriceAdmin(admin.ModelAdmin):
    list_display = ("share", "price", "recorded_at")
    list_filter = ("share",)
    date_hierarchy = "recorded_at"
