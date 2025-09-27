"""Config flow for Snapraid Stats integration."""
from __future__ import annotations

import asyncio
import logging
import socket
from io import StringIO
from typing import Any

import paramiko
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    AUTH_TYPE_PASSWORD,
    AUTH_TYPE_SSH_KEY,
    CONF_AUTH_TYPE,
    CONF_SSH_KEY,
    CONF_SUDO_METHOD,
    CONF_SUDO_PASSWORD,
    DEFAULT_AUTH_TYPE,
    DEFAULT_PORT,
    DEFAULT_SUDO_METHOD,
    DOMAIN,
    SSH_COMMAND_TIMEOUT,
    SSH_TIMEOUT,
    SUDO_METHOD_PASSWORD,
    SUDO_METHOD_PASSWORDLESS,
    SUDO_METHOD_SSH_PASSWORD,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_AUTH_TYPE, default=DEFAULT_AUTH_TYPE): vol.In([AUTH_TYPE_PASSWORD, AUTH_TYPE_SSH_KEY]),
        vol.Optional(CONF_PASSWORD): str,
        vol.Optional(CONF_SSH_KEY): vol.All(str, vol.Length(max=8192)),
        vol.Required(CONF_SUDO_METHOD, default=DEFAULT_SUDO_METHOD): vol.In([
            SUDO_METHOD_PASSWORDLESS,
            SUDO_METHOD_PASSWORD,
            SUDO_METHOD_SSH_PASSWORD
        ]),
        vol.Optional(CONF_SUDO_PASSWORD): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    host = data[CONF_HOST]
    username = data[CONF_USERNAME]
    auth_type = data.get(CONF_AUTH_TYPE, DEFAULT_AUTH_TYPE)
    password = data.get(CONF_PASSWORD)
    ssh_key = data.get(CONF_SSH_KEY)
    sudo_method = data.get(CONF_SUDO_METHOD, DEFAULT_SUDO_METHOD)
    sudo_password = data.get(CONF_SUDO_PASSWORD)
    port = data[CONF_PORT]

    # Validate authentication parameters
    if auth_type == AUTH_TYPE_PASSWORD and not password:
        raise Exception("Password is required for password authentication")
    if auth_type == AUTH_TYPE_SSH_KEY and not ssh_key:
        raise Exception("SSH key is required for SSH key authentication")

    # Validate sudo parameters
    if sudo_method == SUDO_METHOD_PASSWORD and not sudo_password:
        raise Exception("Sudo password is required for sudo password authentication")

    # Test SSH connection using paramiko
    def _test_ssh_connection():
        client = None
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Prepare connection parameters
            connect_kwargs = {
                "hostname": host,
                "port": port,
                "username": username,
                "timeout": SSH_TIMEOUT,
                "allow_agent": False,
                "look_for_keys": False,
            }

            if auth_type == AUTH_TYPE_PASSWORD:
                connect_kwargs["password"] = password
            elif auth_type == AUTH_TYPE_SSH_KEY:
                # Parse SSH key - try different key types
                key_obj = None
                ssh_key_clean = ssh_key.strip()

                # Validate key format
                if not ssh_key_clean:
                    raise Exception("SSH key cannot be empty")

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
                        _LOGGER.debug("Failed to parse as %s key: %s", key_type_name, err)
                        continue

                if key_obj is None:
                    error_msg = f"Invalid SSH key format. Last error: {last_error}"
                    _LOGGER.error(error_msg)
                    raise Exception(error_msg)

                connect_kwargs["pkey"] = key_obj

            # Connect with timeout
            client.connect(**connect_kwargs)

            # Test basic command
            stdin, stdout, stderr = client.exec_command("echo test", timeout=SSH_TIMEOUT)
            exit_status = stdout.channel.recv_exit_status()

            if exit_status != 0:
                error_msg = stderr.read().decode().strip()
                _LOGGER.error("SSH test command failed: %s", error_msg)
                raise CannotConnect

            # Test sudo functionality
            try:
                if sudo_method == SUDO_METHOD_PASSWORDLESS:
                    # Test passwordless sudo
                    stdin, stdout, stderr = client.exec_command("sudo -n true", timeout=SSH_COMMAND_TIMEOUT)
                    exit_status = stdout.channel.recv_exit_status()
                    if exit_status != 0:
                        _LOGGER.warning("Passwordless sudo not configured. Error: %s", stderr.read().decode())
                        raise Exception("Passwordless sudo is not configured for this user")

                elif sudo_method == SUDO_METHOD_PASSWORD:
                    # Test sudo with password
                    stdin, stdout, stderr = client.exec_command("sudo -S true", timeout=SSH_COMMAND_TIMEOUT)
                    stdin.write(f"{sudo_password}\n")
                    stdin.flush()
                    exit_status = stdout.channel.recv_exit_status()
                    if exit_status != 0:
                        _LOGGER.error("Sudo password authentication failed: %s", stderr.read().decode())
                        raise Exception("Sudo password authentication failed")

                elif sudo_method == SUDO_METHOD_SSH_PASSWORD:
                    # Test sudo with SSH password
                    if auth_type == AUTH_TYPE_PASSWORD:
                        stdin, stdout, stderr = client.exec_command("sudo -S true", timeout=SSH_COMMAND_TIMEOUT)
                        stdin.write(f"{password}\n")
                        stdin.flush()
                        exit_status = stdout.channel.recv_exit_status()
                        if exit_status != 0:
                            _LOGGER.error("Sudo with SSH password failed: %s", stderr.read().decode())
                            raise Exception("Sudo with SSH password failed")
                    else:
                        raise Exception("SSH password sudo method only works with password authentication")

                # Test snapraid command if sudo works
                _LOGGER.debug("Testing snapraid command with sudo method: %s", sudo_method)
                stdin, stdout, stderr = client.exec_command("sudo snapraid --version", timeout=SSH_COMMAND_TIMEOUT)
                if sudo_method == SUDO_METHOD_PASSWORD:
                    stdin.write(f"{sudo_password}\n")
                    stdin.flush()
                elif sudo_method == SUDO_METHOD_SSH_PASSWORD and auth_type == AUTH_TYPE_PASSWORD:
                    stdin.write(f"{password}\n")
                    stdin.flush()

                exit_status = stdout.channel.recv_exit_status()
                if exit_status != 0:
                    _LOGGER.warning("Snapraid command test failed, but proceeding: %s", stderr.read().decode())

            except Exception as err:
                _LOGGER.error("Sudo/Snapraid test failed: %s", err)
                raise

        except paramiko.AuthenticationException as err:
            _LOGGER.error("SSH authentication failed: %s", err)
            raise InvalidAuth
        except socket.timeout as err:
            _LOGGER.error("SSH connection timed out: %s", err)
            raise CannotConnect
        except (paramiko.SSHException, socket.error) as err:
            _LOGGER.error("SSH connection failed: %s", err)
            raise CannotConnect
        except Exception as err:
            _LOGGER.error("Unexpected error during SSH test: %s", err)
            # Check if it's an SSH key related error
            if "SSH key" in str(err) or "private key" in str(err):
                raise InvalidAuth
            raise CannotConnect
        finally:
            if client:
                client.close()

    # Run SSH connection test in executor to avoid blocking
    try:
        await hass.async_add_executor_job(_test_ssh_connection)
    except (InvalidAuth, CannotConnect):
        raise
    except Exception as err:
        _LOGGER.error("Failed to test SSH connection: %s", err)
        raise CannotConnect

    return {"title": f"Snapraid Stats ({host})"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Snapraid Stats."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Snapraid Stats."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Update the config entry
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=user_input
                )
                return self.async_create_entry(title="", data={})

        # Pre-fill with current values
        suggested_values = {
            CONF_HOST: self.config_entry.data.get(CONF_HOST, ""),
            CONF_USERNAME: self.config_entry.data.get(CONF_USERNAME, ""),
            CONF_AUTH_TYPE: self.config_entry.data.get(CONF_AUTH_TYPE, DEFAULT_AUTH_TYPE),
            CONF_PASSWORD: self.config_entry.data.get(CONF_PASSWORD, ""),
            CONF_SSH_KEY: self.config_entry.data.get(CONF_SSH_KEY, ""),
            CONF_SUDO_METHOD: self.config_entry.data.get(CONF_SUDO_METHOD, DEFAULT_SUDO_METHOD),
            CONF_SUDO_PASSWORD: self.config_entry.data.get(CONF_SUDO_PASSWORD, ""),
            CONF_PORT: self.config_entry.data.get(CONF_PORT, DEFAULT_PORT),
        }

        options_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=suggested_values[CONF_HOST]): str,
                vol.Required(CONF_USERNAME, default=suggested_values[CONF_USERNAME]): str,
                vol.Required(CONF_AUTH_TYPE, default=suggested_values[CONF_AUTH_TYPE]): vol.In([AUTH_TYPE_PASSWORD, AUTH_TYPE_SSH_KEY]),
                vol.Optional(CONF_PASSWORD, default=suggested_values[CONF_PASSWORD]): str,
                vol.Optional(CONF_SSH_KEY, default=suggested_values[CONF_SSH_KEY]): vol.All(str, vol.Length(max=8192)),
                vol.Required(CONF_SUDO_METHOD, default=suggested_values[CONF_SUDO_METHOD]): vol.In([
                    SUDO_METHOD_PASSWORDLESS,
                    SUDO_METHOD_PASSWORD,
                    SUDO_METHOD_SSH_PASSWORD
                ]),
                vol.Optional(CONF_SUDO_PASSWORD, default=suggested_values[CONF_SUDO_PASSWORD]): str,
                vol.Optional(CONF_PORT, default=suggested_values[CONF_PORT]): int,
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""