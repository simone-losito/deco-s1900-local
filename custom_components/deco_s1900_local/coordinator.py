"""Data coordinator for Deco S1900 Local."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntryAuthFailed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DecoAuthError, DecoConnectionError, DecoS1900Api
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class DecoS1900Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch and coordinate Deco data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: DecoS1900Api,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=max(15, scan_interval)),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.get_all()
        except DecoAuthError as err:
            raise ConfigEntryAuthFailed("Deco authentication expired") from err
        except DecoConnectionError as err:
            raise UpdateFailed(f"Unable to reach the Deco: {err}") from err
        except Exception as err:
            raise UpdateFailed(str(err)) from err
