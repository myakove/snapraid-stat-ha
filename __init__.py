"""The Snapraid Stats integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SNAPRAID_DIFF_CMD,
    SNAPRAID_STATUS_CMD,
    SSH_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Snapraid Stats from a config entry."""
    coordinator = SnapraidStatsDataUpdateCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


class SnapraidStatsDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Snapraid server."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.host = entry.data[CONF_HOST]
        self.username = entry.data[CONF_USERNAME]
        self.password = entry.data[CONF_PASSWORD]
        self.port = entry.data[CONF_PORT]

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, str]:
        """Update data via library."""
        try:
            return await self._get_snapraid_stats()
        except Exception as exception:
            raise UpdateFailed(exception) from exception

    async def _get_snapraid_stats(self) -> dict[str, str]:
        """Get snapraid statistics from the remote server."""
        _LOGGER.debug("Getting snapraid stats from %s", self.host)
        stats = {}

        try:
            # Get status information
            status_output = await self._run_ssh_command(SNAPRAID_STATUS_CMD)
            if status_output:
                status_lines = status_output.strip().splitlines()
                if len(status_lines) >= 5:
                    # Get the last 5 lines for status information
                    status_info = status_lines[-5:]
                    stats.update({
                        "sync_in_progress": status_info[0].strip(),
                        "array_not_scrubbed": status_info[1].strip(),
                        "file_with_zero_sub_second_timestamp": status_info[2].strip(),
                        "rehash": status_info[3].strip(),
                        "errors": status_info[4].strip(),
                    })

            # Get diff information
            diff_output = await self._run_ssh_command(SNAPRAID_DIFF_CMD)
            if diff_output:
                diff_lines = diff_output.strip().splitlines()
                if len(diff_lines) >= 8:
                    # Get the last 8 lines for diff information
                    diff_info = diff_lines[-8:]
                    stats.update({
                        "equal": diff_info[0].split()[0].strip() if diff_info[0].split() else "0",
                        "added": diff_info[1].split()[0].strip() if diff_info[1].split() else "0",
                        "removed": diff_info[2].split()[0].strip() if diff_info[2].split() else "0",
                        "updated": diff_info[3].split()[0].strip() if diff_info[3].split() else "0",
                        "moved": diff_info[4].split()[0].strip() if diff_info[4].split() else "0",
                        "copied": diff_info[5].split()[0].strip() if diff_info[5].split() else "0",
                        "restored": diff_info[6].split()[0].strip() if diff_info[6].split() else "0",
                    })

        except Exception as err:
            _LOGGER.error("Error getting snapraid stats: %s", err)
            raise

        return stats

    async def _run_ssh_command(self, command: str) -> str:
        """Run a command on the remote server via SSH."""
        # Escape password to handle special characters
        escaped_password = self.password.replace("'", "'\"'\"'")

        ssh_command = (
            f"sshpass -p '{escaped_password}' ssh -o StrictHostKeyChecking=no "
            f"-o ConnectTimeout={SSH_TIMEOUT} -o BatchMode=no "
            f"-p {self.port} {self.username}@{self.host} "
            f"'{command}'"
        )

        try:
            proc = await asyncio.create_subprocess_shell(
                ssh_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=SSH_TIMEOUT * 2)

            if proc.returncode != 0:
                error_msg = stderr.decode().strip()
                _LOGGER.error("SSH command failed (return code %d): %s", proc.returncode, error_msg)
                raise Exception(f"SSH command failed: {error_msg}")

            return stdout.decode().strip()

        except asyncio.TimeoutError:
            _LOGGER.error("SSH command timed out after %d seconds", SSH_TIMEOUT * 2)
            raise Exception("SSH command timed out")
        except Exception as err:
            _LOGGER.error("Error running SSH command '%s': %s", command, err)
            raise