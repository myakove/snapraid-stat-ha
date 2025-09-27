"""Constants for the Snapraid Stats integration."""

DOMAIN = "snapraid_stats"

# Configuration keys
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_PORT = "port"
CONF_SUDO_METHOD = "sudo_method"
CONF_SUDO_PASSWORD = "sudo_password"
CONF_DEBUG_LOGGING = "debug_logging"
CONF_DEVICE_NAME = "device_name"


# Sudo methods
SUDO_METHOD_PASSWORDLESS = "passwordless"
SUDO_METHOD_PASSWORD = "password"
SUDO_METHOD_SSH_PASSWORD = "ssh_password"

# Default values
DEFAULT_PORT = 22
DEFAULT_SCAN_INTERVAL = 3600  # 1 hour in seconds
DEFAULT_SUDO_METHOD = SUDO_METHOD_PASSWORDLESS
DEFAULT_DEBUG_LOGGING = False
DEFAULT_DEVICE_NAME = "SnapRaid"

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