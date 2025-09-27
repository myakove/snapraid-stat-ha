"""Constants for the Snapraid Stats integration."""

DOMAIN = "snapraid_stats"

# Configuration keys
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_PORT = "port"

# Default values
DEFAULT_PORT = 22
DEFAULT_SCAN_INTERVAL = 3600  # 1 hour in seconds

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

# SSH timeout
SSH_TIMEOUT = 30