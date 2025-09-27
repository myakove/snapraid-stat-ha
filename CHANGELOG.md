# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.1] - 2025-09-27

### Fixed
- SSH key input field character limit preventing long private keys from being entered
- Better user guidance distinguishing private keys from public keys
- Improved error messages for SSH key authentication issues
- Enhanced UI descriptions to help users locate correct key files

### Changed
- Increased SSH key field maximum length to 8192 characters
- Updated translation strings for clearer SSH key guidance

## [1.2.0] - 2025-09-27

### Added
- SSH key authentication support (RSA, Ed25519, ECDSA, DSS key types)
- Comprehensive sudo support for snapraid commands with three methods:
  - Passwordless sudo (recommended)
  - Sudo with password
  - Sudo using SSH password
- Improved SSH connection timeouts and error handling
- Better SSH key parsing with support for multiple key formats
- Enhanced validation during integration setup
- Comprehensive documentation for SSH key and sudo setup

### Changed
- Replaced sshpass dependency with paramiko library for better SSH handling
- Increased SSH timeouts for better reliability (60s connection, 120s commands)
- Improved error messages and validation feedback
- Enhanced security with proper SSH key handling

### Fixed
- HACS installation issues by correcting repository structure
- SSH connection timeout errors
- SSH key parsing errors for different key formats
- Sudo privilege requirements for snapraid commands
- Connection validation during setup

## [1.0.0] - 2025-09-27

### Added
- Initial release of Snapraid Stats Home Assistant integration
- HACS compatibility for easy installation and updates
- GUI configuration flow for initial setup
- Reconfiguration support through Home Assistant UI
- SSH-based connection to remote snapraid servers
- Real-time monitoring of snapraid status and diff information
- Automatic error detection and reporting
- Comprehensive sensor attributes including:
  - Sync status information
  - File change statistics (added, removed, updated, moved, copied, restored)
  - Error reporting
  - Total changes calculation
- Secure credential storage
- Proper error handling and timeout management
- Debug logging support

### Security
- Password escaping for special characters in SSH connections
- Secure storage of SSH credentials in Home Assistant
- Timeout protection for SSH commands
- Input validation for all configuration parameters

### Documentation
- Comprehensive README with installation and configuration instructions
- Troubleshooting guide
- Automation examples
- Security considerations

### Migration from AppDaemon
- Converted from AppDaemon app to native Home Assistant integration
- Replaced `rrmngmnt` library with native SSH subprocess calls
- Implemented async/await pattern for better performance
- Added proper Home Assistant logging integration
- Improved error handling and connection management