import logging

from . import history

logger = logging.getLogger("main")

# Steps run after every price update, in order; a failing step does not stop the rest
PRICE_UPDATE_STEPS = [history.record_prices]


def on_prices_updated(shares, updated_at):
    """Called by the price update task with the shares whose price was refreshed."""
    for step in PRICE_UPDATE_STEPS:
        try:
            step(shares, updated_at)
        except Exception:
            logger.exception(f"Price update step {step.__module__}.{step.__name__} failed")
