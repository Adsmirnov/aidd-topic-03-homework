"""The only module that imports the T-Invest SDK.

The project uses `tinkoff-investments` 0.2.0b117 (module `tinkoff.invest`).
The current SDK is `t-tech-investments` >= 1.49.2 (module `t_tech.invest`) with
a bundled Russian Trusted Root CA (enabled by SSL_TBANK_VERIFY=True); moving to
it means changing the imports below. See ANALYSIS.md, section 18.
"""

from django.conf import settings
from tinkoff.invest import CandleInterval, Client
from tinkoff.invest.utils import now, quotation_to_decimal

__all__ = ["CandleInterval", "now", "quotation_to_decimal", "tinkoff_client"]


def tinkoff_client():
    """T-Invest API client authorized with the token from settings."""
    return Client(settings.TINKOFF_TOKEN, target=settings.TINKOFF_API_TARGET)
