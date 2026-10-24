def notifications(request):
    """Number of unread notifications for the header."""
    if not request.user.is_authenticated:
        return {}
    return {
        "unread_notifications": request.user.notifications.filter(read_at__isnull=True).count()
    }
