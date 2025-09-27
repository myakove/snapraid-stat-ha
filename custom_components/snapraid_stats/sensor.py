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
from .const import CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME, DOMAIN, SENSOR_NAME, SENSOR_UNIQUE_ID, STATE_ERROR, STATE_OK, STATE_RUNNING, STATE_UNAVAILABLE

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
        self._host = config_entry.data[CONF_HOST]
        self._config_entry = config_entry

        _LOGGER.info("Initializing sensor for %s (%s)", self._device_name, self._host)

        # Use just "Stats" to avoid duplication when device name is "SnapRaid"
        self._attr_name = f"{self._device_name} Stats"
        # Create stable unique ID based on host and domain for persistence
        self._attr_unique_id = f"{DOMAIN}_{self._host}_{SENSOR_UNIQUE_ID}"
        _LOGGER.info("Setting sensor unique ID: %s", self._attr_unique_id)
        self._attr_icon = "mdi:harddisk"
        # Ensure proper platform identification
        self._attr_has_entity_name = False  # Use explicit naming instead
        # Set device info directly to ensure proper association
        # Note: sw_version will be updated with actual snapraid version after first update
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._host)},
            "name": f"{self._device_name} ({self._host})",
            "manufacturer": "Home Assistant Community",
            "model": "SnapRaid Stats Integration",
            "sw_version": "Unknown",
        }


    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        # Check if currently updating
        if hasattr(self.coordinator, '_is_updating') and self.coordinator._is_updating:
            return STATE_RUNNING

        if not self.coordinator.last_update_success:
            return STATE_UNAVAILABLE

        if not self.coordinator.data:
            return STATE_UNAVAILABLE

        # Update device info with snapraid version if available
        if hasattr(self.coordinator, 'snapraid_version') and self.coordinator.snapraid_version:
            current_version = self._attr_device_info.get("sw_version", "Unknown")
            coordinator_version = self.coordinator.snapraid_version

            _LOGGER.debug("Version check - Current: %s, Coordinator: %s", current_version, coordinator_version)

            if coordinator_version != "Unknown" and current_version != coordinator_version:
                _LOGGER.info("Updating device firmware version from %s to %s", current_version, coordinator_version)
                self._attr_device_info["sw_version"] = coordinator_version
                # Force device registry update
                self.async_write_ha_state()
                # Also schedule a device registry update
                if hasattr(self, 'registry_entry') and self.registry_entry:
                    _LOGGER.debug("Scheduling device registry update")
            elif coordinator_version == "Unknown":
                _LOGGER.debug("Coordinator version is still Unknown, not updating device info")

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

