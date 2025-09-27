"""Config flow for Snapraid Stats integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DEFAULT_PORT, DOMAIN, SSH_TIMEOUT

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    host = data[CONF_HOST]
    username = data[CONF_USERNAME]
    password = data[CONF_PASSWORD]
    port = data[CONF_PORT]

    # Test SSH connection
    try:
        # Escape password to handle special characters
        escaped_password = password.replace("'", "'\"'\"'")

        proc = await asyncio.create_subprocess_shell(
            f"sshpass -p '{escaped_password}' ssh -o StrictHostKeyChecking=no "
            f"-o ConnectTimeout={SSH_TIMEOUT} -o BatchMode=no "
            f"-p {port} {username}@{host} 'echo test'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=SSH_TIMEOUT)

        if proc.returncode != 0:
            stderr_text = stderr.decode().lower()
            if any(err in stderr_text for err in ["permission denied", "authentication failed", "access denied"]):
                raise InvalidAuth
            if any(err in stderr_text for err in ["connection refused", "no route to host", "network unreachable"]):
                raise CannotConnect
            _LOGGER.error("SSH connection failed: %s", stderr.decode())
            raise CannotConnect

    except asyncio.TimeoutError:
        _LOGGER.error("SSH connection timeout to %s:%s", host, port)
        raise CannotConnect
    except (InvalidAuth, CannotConnect):
        raise
    except Exception as err:
        _LOGGER.error("Unexpected error during SSH test: %s", err)
        raise CannotConnect

    # Test snapraid command
    try:
        proc = await asyncio.create_subprocess_shell(
            f"sshpass -p '{password}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout={SSH_TIMEOUT} "
            f"-p {port} {username}@{host} 'sudo snapraid --version'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=SSH_TIMEOUT)

        if proc.returncode != 0:
            _LOGGER.warning("Snapraid command test failed, but proceeding: %s", stderr.decode())

    except Exception as err:
        _LOGGER.warning("Could not test snapraid command: %s", err)

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
            CONF_PASSWORD: self.config_entry.data.get(CONF_PASSWORD, ""),
            CONF_PORT: self.config_entry.data.get(CONF_PORT, DEFAULT_PORT),
        }

        options_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=suggested_values[CONF_HOST]): str,
                vol.Required(CONF_USERNAME, default=suggested_values[CONF_USERNAME]): str,
                vol.Required(CONF_PASSWORD, default=suggested_values[CONF_PASSWORD]): str,
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