# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.3] - 2025-11-30

### Fixed

- Correct HACS release zip directory structure
- Add `hacs.json` for proper HACS installation support

## [0.1.2] - 2025-11-29

### Changed

- HA 2025.11 compatibility improvements

### Fixed

- Resolve mypy type errors in CI
- Use `--extra dev` instead of `--dev` for `uv sync`
- CI pipeline issues
- Exclude `__pycache__` from release zip
- Configure HACS zip release with correct filename

## [0.1.0] - 2025-11-29

### Added

- Initial release: LaMotte WaterLink Spin Touch Bluetooth LE integration
- Auto-discovery via Bluetooth service UUID and device name patterns
- Push-based updates with auto-disconnect/reconnect cycle
- Water quality sensors: Free Chlorine, Total Chlorine, Bromine, pH, Total Alkalinity,
  Calcium Hardness, Cyanuric Acid, Salt, Copper, Iron, Phosphate, Borate
- Calculated sensors: Combined Chlorine, FC/CYA Ratio, Water Quality status
- Diagnostic sensors and Force Reconnect button
- SpinDisk series 203, 204, 303, 304, and 402 support
- State persistence via RestoreEntity across restarts
- ESPHome Bluetooth Proxy support

<!-- Version comparison links -->
[Unreleased]: https://github.com/joyfulhouse/lamotte-spintouch/compare/v0.1.3...HEAD
[0.1.3]: https://github.com/joyfulhouse/lamotte-spintouch/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/joyfulhouse/lamotte-spintouch/compare/v0.1.0...v0.1.2
[0.1.0]: https://github.com/joyfulhouse/lamotte-spintouch/releases/tag/v0.1.0
