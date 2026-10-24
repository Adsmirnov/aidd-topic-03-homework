from django.conf import settings
from tinkoff.invest import Client


def tinkoff_client():
    """T-Invest API client authorized with the token from settings."""
    return Client(settings.TINKOFF_TOKEN)
