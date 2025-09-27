# Snapraid Stats Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/myakove/snapraid-stat-ha)](https://github.com/myakove/snapraid-stat-ha/releases)
[![GitHub](https://img.shields.io/github/license/myakove/snapraid-stat-ha)](LICENSE)

A Home Assistant custom integration that monitors Snapraid array statistics from a remote server via SSH.

## Features

- **Real-time Monitoring**: Get live snapraid status and diff information
- **HACS Support**: Easy installation and updates through HACS
- **GUI Configuration**: Set up and reconfigure through Home Assistant UI
- **Error Detection**: Automatically detects and reports snapraid errors
- **Rich Attributes**: Comprehensive statistics including sync status, file changes, and error information
- **Secure**: Uses SSH with proper authentication and timeout handling

## Requirements

### Server Requirements
- Snapraid installed and configured on the target server
- SSH server running on the target machine
- `sudo` access for the configured user to run snapraid commands

### Home Assistant Requirements
- Home Assistant 2023.1 or newer
- HACS (Home Assistant Community Store) for easy installation

## Installation

### Via HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add `https://github.com/myakove/snapraid-stat-ha` as an Integration
6. Search for "Snapraid Stats" and install

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/myakove/snapraid-stat-ha/releases)
2. Extract the contents
3. Copy the `custom_components/snapraid_stats` folder to your Home Assistant `custom_components` directory
4. Restart Home Assistant

## Configuration

### Initial Setup

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Snapraid Stats"
4. Enter your server connection details:
   - **Host**: IP address or hostname of your snapraid server
   - **Username**: SSH username
   - **Authentication Type**: Choose between "Password" or "SSH Key"
   - **Password**: SSH password (required for password authentication)
   - **SSH Private Key**: SSH private key content (required for SSH key authentication)
   - **Sudo Method**: How to handle sudo commands for snapraid
     - **Passwordless**: User has passwordless sudo configured (recommended)
     - **Password**: Use separate sudo password
     - **SSH Password**: Use SSH password for sudo
   - **Sudo Password**: Required if using "Password" sudo method
   - **Port**: SSH port (default: 22)

### Reconfiguration

To update your connection settings:

1. Go to **Settings** → **Devices & Services**
2. Find the "Snapraid Stats" integration
3. Click **Configure**
4. Update your connection details as needed

## Entity Information

The integration creates a single sensor entity: `sensor.snapraid_stats`

### States

- **OK**: Snapraid array is healthy, no errors detected
- **Error**: Snapraid has detected errors in the array
- **Unavailable**: Cannot connect to server or retrieve data

### Attributes

The sensor provides the following attributes with snapraid statistics:

#### Status Information
- `sync_in_progress`: Current sync status
- `array_not_scrubbed`: Scrub status information
- `file_with_zero_sub_second_timestamp`: File timestamp issues
- `rehash`: Rehash status
- `errors`: Error information from snapraid status

#### Diff Information
- `equal`: Number of files that are equal
- `added`: Number of added files
- `removed`: Number of removed files
- `updated`: Number of updated files
- `moved`: Number of moved files
- `copied`: Number of copied files
- `restored`: Number of restored files

#### Additional Information
- `total_changes`: Sum of all file changes (computed)
- `host`: Target server hostname/IP
- `last_updated`: Timestamp of last successful update

## Automation Examples

### Alert on Snapraid Errors

```yaml
automation:
  - alias: "Snapraid Error Alert"
    trigger:
      - platform: state
        entity_id: sensor.snapraid_stats
        to: "Error"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "Snapraid Error Detected"
          message: >
            Snapraid has detected errors on {{ state_attr('sensor.snapraid_stats', 'host') }}.
            Error details: {{ state_attr('sensor.snapraid_stats', 'errors') }}
```

### Alert on High Number of Changes

```yaml
automation:
  - alias: "Snapraid High Changes Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.snapraid_stats
        attribute: total_changes
        above: 100
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "Snapraid: Many File Changes"
          message: >
            {{ state_attr('sensor.snapraid_stats', 'total_changes') }} file changes detected.
            Consider running a snapraid sync.
```

## Troubleshooting

### Common Issues

#### "Cannot connect" error
- Verify the host IP/hostname is correct and reachable
- Check that SSH is running on the target server
- Ensure the SSH port is correct (default: 22)
- Verify network connectivity between Home Assistant and the target server

#### "Invalid authentication" error
- **For password authentication**:
  - Check that the username and password are correct
  - Ensure the user has SSH access to the server
  - Verify that password authentication is enabled in SSH config
- **For SSH key authentication**:
  - Ensure the SSH key format is correct (copy entire key including headers)
  - Verify the public key is installed on the server (`~/.ssh/authorized_keys`)
  - Check that the private key matches the public key on the server
  - Ensure SSH key authentication is enabled on the server

#### "Command failed" errors
- **Snapraid Installation**: Ensure snapraid is installed on the target server
- **Sudo Access**: Verify the user has sudo access to run snapraid commands
- **Sudo Configuration**: Check that the selected sudo method is properly configured
  - For passwordless: Test with `sudo -n snapraid --version`
  - For password: Verify the sudo password is correct
  - For SSH password: Ensure SSH and sudo passwords match
- **Snapraid Config**: Check that snapraid configuration is valid
- **Permissions**: Verify snapraid executable permissions and location

#### Sensor shows "Unavailable"
- Check Home Assistant logs for detailed error messages
- Ensure SSH connection is stable
- Verify network connectivity between Home Assistant and target server

### Enable Debug Logging

Add this to your `configuration.yaml` to enable debug logging:

```yaml
logger:
  logs:
    custom_components.snapraid_stats: debug
```

## Security Considerations

- SSH credentials are stored securely in Home Assistant's encrypted storage
- Uses paramiko library for secure SSH connections (no external dependencies)
- SSH connections use proper timeout and error handling
- **SSH Key Authentication**: Supports RSA, Ed25519, ECDSA, and DSS key types for enhanced security
- Password and SSH key authentication methods available
- SSH keys are more secure than passwords and recommended for production use
- Ensure your snapraid server has proper firewall rules
- Use strong passwords for SSH access or configure SSH key authentication
- Regularly update both Home Assistant and the target server

### Setting up SSH Key Authentication

For enhanced security, you can use SSH key authentication:

1. **Generate SSH Key Pair** (on your client machine):
   ```bash
   ssh-keygen -t ed25519 -C "snapraid-stats@homeassistant"
   ```

2. **Copy Public Key to Server**:
   ```bash
   ssh-copy-id -i ~/.ssh/id_ed25519.pub username@your-server-ip
   ```

3. **Get Private Key Content**:
   ```bash
   cat ~/.ssh/id_ed25519
   ```

4. **Configure Integration**:
   - Set Authentication Type to "SSH Key"
   - Paste the entire private key content (including `-----BEGIN` and `-----END` lines)
   - Leave password field empty

5. **Test Connection**: The integration will validate the SSH key during setup

### Setting up Sudo Access for Snapraid

Snapraid commands require root privileges. Choose one of these sudo configuration methods:

#### Option 1: Passwordless Sudo (Recommended)

Configure the user to run snapraid commands without a password prompt:

1. **Edit sudoers file**:
   ```bash
   sudo visudo
   ```

2. **Add snapraid-specific rule**:
   ```bash
   # Allow user to run snapraid without password
   username ALL=(root) NOPASSWD: /usr/bin/snapraid
   ```

3. **Test configuration**:
   ```bash
   sudo -n snapraid --version
   ```

#### Option 2: Sudo with Password

If you prefer to use a sudo password:

1. **Configure Integration**: Set Sudo Method to "Password"
2. **Enter Sudo Password**: Provide the user's sudo password
3. **Test**: The integration will test sudo access during setup

#### Option 3: Use SSH Password for Sudo

If the SSH user password is the same as the sudo password:

1. **Configure Integration**: Set Sudo Method to "SSH Password"
2. **Requirement**: Only works with password-based SSH authentication
3. **Automatic**: Uses the SSH password for sudo commands

**Security Note**: Passwordless sudo is recommended for automated systems as it's more secure and reliable than storing passwords.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you encounter any issues or have questions:

1. Check the [troubleshooting section](#troubleshooting) above
2. Search existing [issues](https://github.com/myakove/snapraid-stat-ha/issues)
3. Create a new issue with detailed information about your problem

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes in each release.