# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-XX

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