"""Constants for the Snapraid Stats integration."""

DOMAIN = "snapraid_stats"

# Configuration keys
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_PORT = "port"
CONF_AUTH_TYPE = "auth_type"
CONF_SSH_KEY = "ssh_key"
CONF_SUDO_METHOD = "sudo_method"
CONF_SUDO_PASSWORD = "sudo_password"

# Authentication types
AUTH_TYPE_PASSWORD = "password"
AUTH_TYPE_SSH_KEY = "ssh_key"

# Sudo methods
SUDO_METHOD_PASSWORDLESS = "passwordless"
SUDO_METHOD_PASSWORD = "password"
SUDO_METHOD_SSH_PASSWORD = "ssh_password"

# Default values
DEFAULT_PORT = 22
DEFAULT_SCAN_INTERVAL = 3600  # 1 hour in seconds
DEFAULT_AUTH_TYPE = AUTH_TYPE_PASSWORD
DEFAULT_SUDO_METHOD = SUDO_METHOD_PASSWORDLESS

# Entity names
SENSOR_NAME = "Snapraid Stats"
SENSOR_UNIQUE_ID = "snapraid_stats"

# States
STATE_OK = "OK"
STATE_ERROR = "Error"
STATE_UNAVAILABLE = "Unavailable"

# Snapraid commands
SNAPRAID_STATUS_CMD = "sudo snapraid status"
SNAPRAID_DIFF_CMD = "sudo snapraid diff"

# SSH timeouts
SSH_TIMEOUT = 60  # Increased for better connectivity
SSH_COMMAND_TIMEOUT = 120  # Longer timeout for snapraid commands