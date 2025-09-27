# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.7] - 2025-09-27

### Fixed
- **Critical**: Enhanced platform setup/unload state handling to resolve persistent reload errors
- Added specific handling for "Config entry was never loaded!" and "already been setup!" errors
- Improved state consistency between setup and unload operations
- More robust error recovery during integration reload cycles
- Better logging for troubleshooting platform state issues

### Improved
- Defensive programming against Home Assistant platform state inconsistencies
- More graceful handling of partial setup/unload failures
- Enhanced debug logging for platform lifecycle events

## [1.3.6] - 2025-09-27

### Fixed
- **Critical**: Fixed integration reload/unload errors when enabling debug logging
- Improved error handling in setup and unload processes
- Added defensive cleanup in case of setup failures
- Resolved "Config entry was never loaded!" errors during reload
- Better handling of platform unload failures

### Improved
- More robust integration lifecycle management
- Enhanced error logging and recovery
- Safer data cleanup during unload operations

## [1.3.5] - 2025-09-27

### Fixed
- **Important**: Corrected device manufacturer from "Snapraid" to "Home Assistant Community"
- Device model updated to "SnapRaid Stats Integration" for clarity
- Properly attributes the integration to the HA community, not the Snapraid project

### Changed
- Device info now correctly reflects this is a community Home Assistant integration
- More accurate attribution and device identification

## [1.3.4] - 2025-09-27

### Fixed
- **Critical**: Simplified entity registration to resolve persistent "entity no longer being provided" warning
- Removed complex entity registry manipulation that could cause registration issues
- Streamlined sensor setup and entity identification
- Should eliminate the recurring entity warning for users without orphaned entities

### Improved
- Cleaner entity registration process
- More reliable entity-integration association
- Simplified sensor initialization

## [1.3.3] - 2025-09-27

### Fixed
- **Critical**: Fixed snapraid version detection by removing unnecessary sudo requirement
- Version command now correctly uses `snapraid --version` instead of `sudo snapraid --version`
- Enhanced error logging and debugging for version detection issues
- Should now properly detect and display versions like "12.4" instead of "Unknown"

### Improved
- Better debug logging for snapraid version detection
- More accurate error messages when version detection fails
- Simplified version detection logic

## [1.3.2] - 2025-09-27

### Added
- **Enhancement**: Device firmware version now shows actual snapraid version instead of static "1.0.0"
- Automatic detection of snapraid version from remote system using `snapraid --version`
- Device info updates dynamically when snapraid version is detected

### Changed
- Device firmware field now displays real snapraid version (e.g., "12.0", "11.6")
- Version detection happens during first data update and caches the result
- Fallback to "Unknown" if version cannot be detected

### Technical
- Added regex parsing for snapraid version output
- Coordinator stores snapraid version for sensor device info updates
- Improved device info accuracy and usefulness

## [1.3.1] - 2025-09-27

### Fixed
- **Critical**: Fixed device association for sensor entities
- Sensors now properly associate with their device instead of appearing in "Ungrouped"
- Set device_info directly in sensor attributes for better device binding
- Updated device software version to match integration version

## [1.3.0] - 2025-09-27

### Added
- **New Feature**: Configurable scan interval (pull interval) in configuration
- Scan interval range: 300 seconds (5 minutes) to 86400 seconds (24 hours)
- Default scan interval remains 3600 seconds (1 hour)
- Available in both initial setup and reconfiguration options

### Changed
- Coordinator now uses configurable scan interval instead of hardcoded value
- More flexible polling frequency for different use cases

## [1.2.11] - 2025-09-27

### Fixed
- Fixed duplicate sensor naming causing "SnapRaid Snapraid Stats" display
- Sensor name now shows as "[Device Name] Stats" (e.g., "SnapRaid Stats")
- Eliminated redundant "Snapraid" text in sensor naming

## [1.2.10] - 2025-09-27

### Fixed
- **Critical**: Fix AttributeError 'last_update_success_time' by switching to TimestampDataUpdateCoordinator
- Sensor now properly tracks and displays last update timestamp in attributes

## [1.2.9] - 2025-09-27

### Changed
- **Breaking**: Simplified authentication to password-only (removed SSH key support)
- Debug logging is now a configurable option instead of always enabled
- Added configurable device name with default "SnapRaid"
- Sensor name now includes device name: "[Device Name] Snapraid Stats"
- Device display name now shows: "[Device Name] (hostname)"

### Removed
- SSH key authentication support (password authentication only)
- Always-on debug logging (now configurable)
- SSH key related configuration fields and validation

### Fixed
- Conditional debug logging reduces log noise when disabled
- Simplified configuration flow for easier setup
- Removed unused SSH key parsing logic

## [1.2.8] - 2025-09-27

### Fixed
- **Critical**: Fix snapraid exit code handling to allow normal exit codes 1 and 2
- Exit code 2 from `snapraid diff` is normal and means "there are differences"
- Exit code 1 from snapraid commands indicates warnings but usable output
- Only fail on exit codes 3+ which indicate actual command failures
- Maintain strict exit code checking for non-snapraid commands

### Added
- Appropriate debug/warning logging for different snapraid exit codes
- Better distinction between normal snapraid behavior and actual failures

### Changed
- Integration no longer fails when snapraid finds differences (the expected case)
- More nuanced error handling based on snapraid's exit code conventions

## [1.2.7] - 2025-09-27

### Fixed
- **Critical**: Replace complex parsing with precise regex pattern matching
- Use regex to match exact snapraid statistics format: `^\s*(\d+)\s+(keyword)$`
- Directly targets format like "  355067 equal", "     676 added"
- Automatically ignores all file paths and non-statistic lines
- Much simpler and more reliable than previous multi-pass parsing

### Changed
- Simplified parsing logic from 45+ lines to ~15 lines using regex
- More precise matching that's immune to file operation format variations
- Enhanced debug logging showing regex matches and statistics found

### Removed
- Complex two-pass parsing logic
- Manual line filtering and keyword detection
- Error-prone string manipulation approaches

## [1.2.6] - 2025-09-27

### Fixed
- **Critical**: Implement robust two-pass parsing for snapraid diff output
- First pass finds where statistics section starts by detecting number+keyword patterns
- Second pass parses only lines that match known statistic keywords (equal, added, removed, etc.)
- Much more resilient to various output formats and file path variations
- Focuses exclusively on extracting the 7 core statistics needed for monitoring

### Added
- Enhanced debug logging showing exact lines being processed and where statistics section starts
- Better detection of statistics vs file operation lines
- More selective parsing that ignores non-statistic content

### Changed
- Replaced simple line filtering with intelligent two-phase parsing
- Improved handling of verbose snapraid output with many file operations

## [1.2.5] - 2025-09-27

### Fixed
- **Critical**: Filter out individual file operations from snapraid diff output parsing
- Skip lines starting with 'add ', 'remove ', 'update ', 'move ', 'copy ', 'restore '
- Focus parsing only on summary statistics lines (e.g., '355067 equal')
- Prevents parsing failures when snapraid output contains hundreds of individual file changes

### Added
- Debug logging showing how many file operation lines were skipped
- Better separation between individual file operations and summary statistics

### Changed
- More targeted parsing that ignores verbose file operation details
- Enhanced debug output for troubleshooting parsing issues

## [1.2.4] - 2025-09-27

### Fixed
- **Critical**: Fixed snapraid output parsing to handle real-world command output
- Integration initialization failure when snapraid produces valid but differently formatted output
- Robust keyword-based parsing instead of fragile line-position parsing
- Support for snapraid diff output containing "There are differences!" message

### Changed
- Parsing logic now searches for "number keyword" patterns (e.g., "355067 equal")
- Enhanced debug logging for output parsing diagnostics
- Fallback values provided when parsing encounters unexpected formats
- Support for variable output formats from different snapraid configurations

### Added
- Comprehensive debug logging showing parsed statistics
- Better error handling for malformed snapraid output
- Default values for missing status information

## [1.2.3] - 2025-09-27

### Added
- Detailed error logging for SSH command failures with stdout/stderr output
- Snapraid availability check using 'which snapraid' command
- Debug logging for SSH command execution
- Enhanced error messages showing exit codes and command details

### Fixed
- Improved SSH key text area implementation using selector module
- Better diagnostics for exit code 2 errors (command not found/invalid usage)
- More informative error reporting for troubleshooting

### Changed
- SSH command error messages now include both stdout and stderr
- Enhanced debugging capabilities for remote command execution

## [1.2.2] - 2025-09-27

### Fixed
- SSH key input field now uses proper multiline text area instead of single-line input
- Users can now paste long SSH private keys (2000+ characters) without issues
- Improved UI rendering for SSH key configuration

### Changed
- Replaced basic string input with TextSelector multiline text area
- Enhanced SSH key field validation and user experience

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