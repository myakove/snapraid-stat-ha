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
    CONF_SUDO_METHOD,
    CONF_SUDO_PASSWORD,
    DEFAULT_AUTH_TYPE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SUDO_METHOD,
    DOMAIN,
    SNAPRAID_DIFF_CMD,
    SNAPRAID_STATUS_CMD,
    SSH_COMMAND_TIMEOUT,
    SSH_TIMEOUT,
    SUDO_METHOD_PASSWORD,
    SUDO_METHOD_PASSWORDLESS,
    SUDO_METHOD_SSH_PASSWORD,
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
        self.sudo_method = entry.data.get(CONF_SUDO_METHOD, DEFAULT_SUDO_METHOD)
        self.sudo_password = entry.data.get(CONF_SUDO_PASSWORD)
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
            # First check if snapraid is available
            try:
                await self._run_ssh_command("which snapraid")
                _LOGGER.debug("Snapraid found on remote system")
            except Exception as err:
                _LOGGER.warning("Snapraid command may not be available: %s", err)

            # Get status information
            status_output = await self._run_ssh_command(SNAPRAID_STATUS_CMD)
            if status_output:
                status_lines = status_output.strip().splitlines()
                _LOGGER.debug("Snapraid status output has %d lines", len(status_lines))

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
                    _LOGGER.debug("Parsed status info from last 5 lines")
                else:
                    _LOGGER.warning("Status output has only %d lines, expected at least 5", len(status_lines))
                    # Provide default values
                    stats.update({
                        "sync_in_progress": "Unknown",
                        "array_not_scrubbed": "Unknown",
                        "file_with_zero_sub_second_timestamp": "Unknown",
                        "rehash": "Unknown",
                        "errors": "Unknown",
                    })

            # Get diff information
            diff_output = await self._run_ssh_command(SNAPRAID_DIFF_CMD)
            if diff_output:
                diff_lines = diff_output.strip().splitlines()
                _LOGGER.debug("Snapraid diff output has %d lines", len(diff_lines))

                # Parse diff statistics - look for lines with numbers and keywords
                stats_dict = {
                    "equal": "0", "added": "0", "removed": "0", "updated": "0",
                    "moved": "0", "copied": "0", "restored": "0"
                }

                skipped_lines = 0

                for line in diff_lines:
                    line = line.strip()
                    if not line:
                        continue

                    # Skip individual file operations (add/remove specific files)
                    if line.startswith(('add ', 'remove ', 'update ', 'move ', 'copy ', 'restore ')):
                        skipped_lines += 1
                        continue

                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            count = int(parts[0])
                            keyword = parts[1].lower()
                            if keyword in stats_dict:
                                stats_dict[keyword] = str(count)
                                _LOGGER.debug("Found %s: %d", keyword, count)
                        except (ValueError, IndexError):
                            continue

                _LOGGER.debug("Skipped %d file operation lines, parsed statistics: %s", skipped_lines, stats_dict)
                stats.update(stats_dict)

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

                # Execute command with sudo handling
                _LOGGER.debug("Executing SSH command: %s", command)
                stdin, stdout, stderr = client.exec_command(command, timeout=SSH_COMMAND_TIMEOUT)

                # Handle sudo password if needed
                if "sudo" in command and self.sudo_method == SUDO_METHOD_PASSWORD:
                    stdin.write(f"{self.sudo_password}\n")
                    stdin.flush()
                elif "sudo" in command and self.sudo_method == SUDO_METHOD_SSH_PASSWORD:
                    if self.auth_type == AUTH_TYPE_PASSWORD:
                        stdin.write(f"{self.password}\n")
                        stdin.flush()

                exit_status = stdout.channel.recv_exit_status()

                # Read output
                stdout_data = stdout.read().decode().strip()
                stderr_data = stderr.read().decode().strip()

                if exit_status != 0:
                    _LOGGER.error("SSH command '%s' failed (exit code %d)", command, exit_status)
                    _LOGGER.error("STDOUT: %s", stdout_data)
                    _LOGGER.error("STDERR: %s", stderr_data)
                    error_msg = stderr_data if stderr_data else stdout_data
                    raise Exception(f"SSH command failed (exit code {exit_status}): {error_msg}")

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