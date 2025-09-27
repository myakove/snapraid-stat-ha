"""The Snapraid Stats integration."""
from __future__ import annotations

import asyncio
import logging
import socket
from datetime import timedelta
from io import StringIO

import paramiko
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    AUTH_TYPE_PASSWORD,
    AUTH_TYPE_SSH_KEY,
    CONF_AUTH_TYPE,
    CONF_SSH_KEY,
    DEFAULT_AUTH_TYPE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SNAPRAID_DIFF_CMD,
    SNAPRAID_STATUS_CMD,
    SSH_COMMAND_TIMEOUT,
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
        self.auth_type = entry.data.get(CONF_AUTH_TYPE, DEFAULT_AUTH_TYPE)
        self.password = entry.data.get(CONF_PASSWORD)
        self.ssh_key = entry.data.get(CONF_SSH_KEY)
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
        """Run a command on the remote server via SSH using paramiko."""
        def _execute_ssh_command():
            client = None
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                # Prepare connection parameters
                connect_kwargs = {
                    "hostname": self.host,
                    "port": self.port,
                    "username": self.username,
                    "timeout": SSH_TIMEOUT,
                    "allow_agent": False,
                    "look_for_keys": False,
                }

                if self.auth_type == AUTH_TYPE_PASSWORD:
                    connect_kwargs["password"] = self.password
                elif self.auth_type == AUTH_TYPE_SSH_KEY:
                    # Parse SSH key - try different key types
                    key_obj = None
                    ssh_key_clean = self.ssh_key.strip()

                    # Try different key types
                    key_types = [
                        ("Ed25519", paramiko.Ed25519Key),
                        ("RSA", paramiko.RSAKey),
                        ("ECDSA", paramiko.ECDSAKey),
                        ("DSS/DSA", paramiko.DSSKey),
                    ]

                    last_error = None
                    for key_type_name, key_class in key_types:
                        try:
                            key_obj = key_class.from_private_key(StringIO(ssh_key_clean))
                            _LOGGER.debug("Successfully parsed %s SSH key", key_type_name)
                            break
                        except Exception as err:
                            last_error = err
                            continue

                    if key_obj is None:
                        error_msg = f"Invalid SSH key format. Last error: {last_error}"
                        _LOGGER.error(error_msg)
                        raise Exception(error_msg)

                    connect_kwargs["pkey"] = key_obj

                # Connect with timeout
                client.connect(**connect_kwargs)

                # Execute command
                stdin, stdout, stderr = client.exec_command(command, timeout=SSH_COMMAND_TIMEOUT)
                exit_status = stdout.channel.recv_exit_status()

                # Read output
                stdout_data = stdout.read().decode().strip()
                stderr_data = stderr.read().decode().strip()

                if exit_status != 0:
                    _LOGGER.error("SSH command failed (exit code %d): %s", exit_status, stderr_data)
                    raise Exception(f"SSH command failed: {stderr_data}")

                return stdout_data

            except paramiko.AuthenticationException as err:
                _LOGGER.error("SSH authentication failed: %s", err)
                raise Exception(f"SSH authentication failed: {err}")
            except socket.timeout as err:
                _LOGGER.error("SSH command timed out after %d seconds: %s", SSH_COMMAND_TIMEOUT, err)
                raise Exception(f"SSH command timed out: {err}")
            except (paramiko.SSHException, socket.error) as err:
                _LOGGER.error("SSH connection failed: %s", err)
                raise Exception(f"SSH connection failed: {err}")
            except Exception as err:
                _LOGGER.error("Error running SSH command '%s': %s", command, err)
                # Check if it's an SSH key related error
                if "SSH key" in str(err) or "private key" in str(err):
                    raise Exception(f"SSH key error: {err}")
                raise Exception(f"SSH command failed: {err}")
            finally:
                if client:
                    client.close()

        try:
            return await self.hass.async_add_executor_job(_execute_ssh_command)
        except Exception as err:
            _LOGGER.error("Failed to execute SSH command: %s", err)
            raise