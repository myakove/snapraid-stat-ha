"""Sensor platform for Snapraid Stats integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SnapraidStatsDataUpdateCoordinator
from .const import CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME, DOMAIN, SENSOR_NAME, SENSOR_UNIQUE_ID, STATE_ERROR, STATE_OK, STATE_UNAVAILABLE

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([SnapraidStatsSensor(coordinator, config_entry)])


class SnapraidStatsSensor(CoordinatorEntity[SnapraidStatsDataUpdateCoordinator], SensorEntity):
    """Representation of a Snapraid Stats sensor."""

    def __init__(
        self,
        coordinator: SnapraidStatsDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_name = config_entry.data.get(CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME)
        self._attr_name = f"{self._device_name} {SENSOR_NAME}"
        self._attr_unique_id = f"{SENSOR_UNIQUE_ID}_{config_entry.entry_id}"
        self._attr_icon = "mdi:harddisk"
        self._host = config_entry.data[CONF_HOST]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, self._host)},
            "name": f"{self._device_name} ({self._host})",
            "manufacturer": "Snapraid",
            "model": "Stats Monitor",
            "sw_version": "1.0.0",
        }

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        if not self.coordinator.last_update_success:
            return STATE_UNAVAILABLE

        if not self.coordinator.data:
            return STATE_UNAVAILABLE

        # Check if there are any errors in the snapraid output
        errors = self.coordinator.data.get("errors", "")
        if "No error detected." not in errors and errors:
            return STATE_ERROR

        return STATE_OK

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}

        attributes = dict(self.coordinator.data)

        # Add some computed attributes for convenience
        if self.coordinator.data:
            total_changes = 0
            for key in ["added", "removed", "updated", "moved", "copied", "restored"]:
                try:
                    total_changes += int(self.coordinator.data.get(key, "0"))
                except (ValueError, TypeError):
                    pass
            attributes["total_changes"] = total_changes

            # Add host information
            attributes["host"] = self._host

            # Add last update time
            if self.coordinator.last_update_success_time:
                attributes["last_updated"] = self.coordinator.last_update_success_time.isoformat()

        return attributes

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success