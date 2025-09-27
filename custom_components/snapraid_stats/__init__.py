"""The Snapraid Stats integration."""
from __future__ import annotations

import asyncio
import logging
import re
import socket
from datetime import timedelta
from io import StringIO

import paramiko
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, TimestampDataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_DEBUG_LOGGING,
    CONF_DEVICE_NAME,
    CONF_SCAN_INTERVAL,
    CONF_SUDO_METHOD,
    CONF_SUDO_PASSWORD,
    DEFAULT_DEBUG_LOGGING,
    DEFAULT_DEVICE_NAME,
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

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Snapraid Stats from a config entry."""
    coordinator = SnapraidStatsDataUpdateCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def _async_entry_updated(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle entry updates."""
    await hass.config_entries.async_reload(config_entry.entry_id)


class SnapraidStatsDataUpdateCoordinator(TimestampDataUpdateCoordinator):
    """Class to manage fetching data from the Snapraid server."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.host = entry.data[CONF_HOST]
        self.username = entry.data[CONF_USERNAME]
        self.password = entry.data[CONF_PASSWORD]
        self.sudo_method = entry.data.get(CONF_SUDO_METHOD, DEFAULT_SUDO_METHOD)
        self.sudo_password = entry.data.get(CONF_SUDO_PASSWORD)
        self.port = entry.data[CONF_PORT]
        self.scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        self.debug_logging = entry.data.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING)
        self.device_name = entry.data.get(CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME)
        self.snapraid_version = None  # Will be set during first update
        self._consecutive_failures = 0  # Track consecutive failures

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=self.scan_interval),
        )

    async def _async_update_data(self) -> dict[str, str]:
        """Update data via library."""
        try:
            _LOGGER.debug("Starting data update for %s (attempt after %d consecutive failures)",
                         self.host, self._consecutive_failures)
            result = await self._get_snapraid_stats()
            _LOGGER.debug("Data update successful for %s, got %d stats", self.host, len(result))
            # Reset failure counter on success
            if self._consecutive_failures > 0:
                _LOGGER.info("Connection to %s recovered after %d failures", self.host, self._consecutive_failures)
                self._consecutive_failures = 0
            return result
        except Exception as exception:
            self._consecutive_failures += 1
            _LOGGER.error("Data update failed for %s (failure #%d): %s",
                         self.host, self._consecutive_failures, exception)

            # Provide different error messages based on failure count
            if self._consecutive_failures <= 3:
                _LOGGER.warning("Temporary connection issue with %s, will retry next update", self.host)
            else:
                _LOGGER.error("Multiple consecutive failures (%d) for %s, check SSH connectivity",
                             self._consecutive_failures, self.host)

            raise UpdateFailed(f"SSH connection failed (attempt #{self._consecutive_failures}): {exception}") from exception

    async def _get_snapraid_stats(self) -> dict[str, str]:
        """Get snapraid statistics from the remote server."""
        _LOGGER.debug("Getting snapraid stats from %s", self.host)
        stats = {}

        try:
            # First check if snapraid is available and get version
            try:
                await self._run_ssh_command("which snapraid")
                _LOGGER.debug("Snapraid found on remote system")

                # Get snapraid version if we haven't already
                if self.snapraid_version is None:
                    try:
                        # Try without sudo first, as version command typically doesn't need root
                        try:
                            version_output = await self._run_ssh_command("snapraid --version")
                            _LOGGER.debug("Snapraid version output (no sudo): %s", version_output)
                        except Exception as no_sudo_err:
                            _LOGGER.debug("Version command failed without sudo: %s, trying with sudo", no_sudo_err)
                            # If that fails, try with sudo
                            version_output = await self._run_ssh_command("sudo snapraid --version")
                            _LOGGER.debug("Snapraid version output (with sudo): %s", version_output)

                        # Parse version from output like "snapraid v12.4 by Andrea Mazzoleni"
                        import re
                        for line in version_output.strip().splitlines():
                            version_match = re.search(r'snapraid v([\d\.]+)', line, re.IGNORECASE)
                            if version_match:
                                self.snapraid_version = version_match.group(1)
                                _LOGGER.info("Detected snapraid version: %s", self.snapraid_version)
                                break

                        if self.snapraid_version is None:
                            _LOGGER.warning("Could not parse snapraid version from: %s", version_output)
                            self.snapraid_version = "Unknown"
                    except Exception as ver_err:
                        _LOGGER.warning("Could not get snapraid version: %s", ver_err)
                        self.snapraid_version = "Unknown"

            except Exception as err:
                _LOGGER.warning("Snapraid command may not be available: %s", err)
                if self.snapraid_version is None:
                    self.snapraid_version = "Unknown"

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

                # Use regex to match statistics pattern: whitespace + number + space + keyword
                # Pattern matches: "     355067 equal", "      676 added", etc.
                stats_pattern = re.compile(r'^\s*(\d+)\s+(equal|added|removed|updated|moved|copied|restored)$')

                stats_dict = {
                    "equal": "0", "added": "0", "removed": "0", "updated": "0",
                    "moved": "0", "copied": "0", "restored": "0"
                }

                matched_lines = 0
                for line in diff_lines:
                    match = stats_pattern.match(line)
                    if match:
                        count = match.group(1)
                        keyword = match.group(2)
                        stats_dict[keyword] = count
                        matched_lines += 1
                        _LOGGER.debug("Regex matched: %s = %s", keyword, count)

                _LOGGER.debug("Found %d statistics using regex from %d total lines: %s",
                            matched_lines, len(diff_lines), stats_dict)
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

                # Use password authentication only
                connect_kwargs["password"] = self.password

                # Connect with timeout
                _LOGGER.debug("Connecting to %s@%s:%d", self.username, self.host, self.port)
                client.connect(**connect_kwargs)
                _LOGGER.debug("SSH connection established to %s", self.host)

                # Test basic connectivity first
                _LOGGER.debug("Testing basic SSH connectivity")
                test_stdin, test_stdout, test_stderr = client.exec_command("echo test", timeout=10)
                test_exit = test_stdout.channel.recv_exit_status()
                if test_exit != 0:
                    _LOGGER.error("Basic SSH connectivity test failed")
                    raise Exception("SSH connectivity test failed")
                _LOGGER.debug("SSH connectivity test passed")

                # Execute command with sudo handling
                _LOGGER.debug("Executing SSH command: %s", command)
                stdin, stdout, stderr = client.exec_command(command, timeout=SSH_COMMAND_TIMEOUT)

                # Handle sudo password if needed
                if "sudo" in command and self.sudo_method == SUDO_METHOD_PASSWORD:
                    stdin.write(f"{self.sudo_password}\n")
                    stdin.flush()
                elif "sudo" in command and self.sudo_method == SUDO_METHOD_SSH_PASSWORD:
                    stdin.write(f"{self.password}\n")
                    stdin.flush()

                exit_status = stdout.channel.recv_exit_status()

                # Read output
                stdout_data = stdout.read().decode().strip()
                stderr_data = stderr.read().decode().strip()

                # Handle exit codes appropriately
                if exit_status != 0:
                    # Handle snapraid-specific exit codes
                    if "snapraid" in command:
                        if exit_status == 2:
                            # Exit code 2: differences found (for diff) or errors detected (for status)
                            _LOGGER.debug("Snapraid exit code 2: differences or errors found (normal operation)")
                        elif exit_status == 1:
                            # Exit code 1: warnings or minor issues (still usable output)
                            _LOGGER.warning("Snapraid exit code 1: warnings detected but continuing")
                        else:
                            # Other exit codes are actual failures
                            _LOGGER.error("SSH command '%s' failed (exit code %d)", command, exit_status)
                            _LOGGER.error("STDOUT: %s", stdout_data)
                            _LOGGER.error("STDERR: %s", stderr_data)
                            error_msg = stderr_data if stderr_data else stdout_data
                            raise Exception(f"SSH command failed (exit code {exit_status}): {error_msg}")
                    else:
                        # Non-snapraid commands should still fail on non-zero exit codes
                        _LOGGER.error("SSH command '%s' failed (exit code %d)", command, exit_status)
                        _LOGGER.error("STDOUT: %s", stdout_data)
                        _LOGGER.error("STDERR: %s", stderr_data)
                        error_msg = stderr_data if stderr_data else stdout_data
                        raise Exception(f"SSH command failed (exit code {exit_status}): {error_msg}")

                return stdout_data

            except paramiko.AuthenticationException as err:
                _LOGGER.error("SSH authentication failed for %s@%s: %s", self.username, self.host, err)
                raise Exception(f"SSH authentication failed: {err}")
            except socket.timeout as err:
                _LOGGER.error("SSH command '%s' timed out after %d seconds on %s: %s",
                             command, SSH_COMMAND_TIMEOUT, self.host, err)
                raise Exception(f"SSH command timed out: {err}")
            except (paramiko.SSHException, socket.error) as err:
                _LOGGER.error("SSH connection failed to %s:%d: %s", self.host, self.port, err)
                raise Exception(f"SSH connection failed: {err}")
            except Exception as err:
                _LOGGER.error("Error running SSH command '%s' on %s: %s", command, self.host, err)
                raise Exception(f"SSH command failed: {err}")
            finally:
                if client:
                    client.close()

        try:
            return await self.hass.async_add_executor_job(_execute_ssh_command)
        except Exception as err:
            _LOGGER.error("Failed to execute SSH command '%s' on %s: %s", command, self.host, err)
            raise