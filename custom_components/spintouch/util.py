"""Utility functions and classes for SpinTouch integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Callable
    from datetime import datetime

    from homeassistant.helpers.restore_state import RestoreEntity

_LOGGER = logging.getLogger(__name__)

# States that indicate no valid data to restore
INVALID_RESTORE_STATES = (None, "unknown", "unavailable")


async def restore_float_state(entity: RestoreEntity) -> float | None:
    """Restore a float value from entity state history.

    Args:
        entity: The RestoreEntity instance to get previous state from.

    Returns:
        The restored float value, or None if restoration failed.
    """
    last_state = await entity.async_get_last_state()
    if last_state is None or last_state.state in INVALID_RESTORE_STATES:
        return None

    try:
        return float(last_state.state)
    except (ValueError, TypeError):
        return None


async def restore_datetime_state(entity: RestoreEntity) -> datetime | None:
    """Restore a datetime value from entity state history.

    Args:
        entity: The RestoreEntity instance to get previous state from.

    Returns:
        The restored datetime value (timezone-aware), or None if restoration failed.
    """
    last_state = await entity.async_get_last_state()
    if last_state is None or last_state.state in INVALID_RESTORE_STATES:
        return None

    try:
        return dt_util.parse_datetime(last_state.state)  # type: ignore[no-any-return]
    except (ValueError, TypeError):
        return None


class TimerManager:
    """Manages scheduled callbacks for the coordinator.

    Provides a clean interface for scheduling and canceling timed callbacks,
    reducing boilerplate in the coordinator and improving testability.
    """

    def __init__(self, hass: HomeAssistant, logger: logging.Logger | None = None) -> None:
        """Initialize the timer manager.

        Args:
            hass: Home Assistant instance for accessing the event loop.
            logger: Optional logger for debug output.
        """
        self._hass = hass
        self._logger = logger or _LOGGER
        self._timers: dict[str, asyncio.TimerHandle] = {}

    def schedule(
        self,
        name: str,
        delay: int,
        callback_fn: Callable[[], None],
    ) -> None:
        """Schedule a callback after a delay.

        Cancels any existing timer with the same name before scheduling.
        This provides "restart" behavior for timers.

        Args:
            name: Unique identifier for this timer (e.g., "disconnect", "reconnect").
            delay: Delay in seconds before the callback is executed.
            callback_fn: Function to call when the timer fires.
        """
        # Cancel existing timer with same name (restart behavior)
        self.cancel(name)

        @callback  # type: ignore[misc]
        def _timer_callback() -> None:
            """Execute callback and clean up timer reference."""
            self._timers.pop(name, None)
            callback_fn()

        self._timers[name] = self._hass.loop.call_later(delay, _timer_callback)
        self._logger.debug("Timer '%s' scheduled for %ds", name, delay)

    def cancel(self, name: str) -> bool:
        """Cancel a scheduled timer.

        Args:
            name: The timer identifier to cancel.

        Returns:
            True if a timer was canceled, False if no timer was found.
        """
        timer = self._timers.pop(name, None)
        if timer:
            timer.cancel()
            self._logger.debug("Timer '%s' canceled", name)
            return True
        return False

    def cancel_all(self) -> None:
        """Cancel all active timers."""
        for name in list(self._timers.keys()):
            self.cancel(name)

    def is_active(self, name: str) -> bool:
        """Check if a timer is currently active.

        Args:
            name: The timer identifier to check.

        Returns:
            True if the timer exists and hasn't fired yet.
        """
        return name in self._timers
