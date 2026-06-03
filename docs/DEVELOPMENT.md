# Development

How to set up a development environment for LaMotte SpinTouch.

## Prerequisites

- Python 3.13+ and [`uv`](https://docs.astral.sh/uv/).
- A LaMotte WaterLink Spin Touch device (or captured BLE data for unit tests).

## Setup

```bash
git clone https://github.com/joyfulhouse/lamotte-spintouch.git
cd lamotte-spintouch
uv sync --extra dev
```

## Quality Checks

```bash
uv run ruff check --fix custom_components/   # lint with auto-fix
uv run ruff format custom_components/        # format
uv run mypy custom_components/               # strict type check
uv run pytest                                # unit tests
```

Run all checks before opening a pull request. See
[CONTRIBUTING](https://github.com/joyfulhouse/.github/blob/main/CONTRIBUTING.md)
for the contribution workflow.

## Deploying to a Local Home Assistant Instance

```bash
cp -r custom_components/spintouch ~/.homeassistant/custom_components/
# Then restart Home Assistant and check logs:
# Settings → System → Logs, filter by "spintouch"
```

Or validate config without starting HA:

```bash
hass --script check_config
```

## ESPHome Direct (Alternative)

For testing the standalone ESPHome firmware:

```bash
esphome compile esphome/spintouch.yaml
esphome upload esphome/spintouch.yaml
esphome logs esphome/spintouch.yaml
```

## Releasing

1. Bump `version` in `custom_components/spintouch/manifest.json` and `pyproject.toml`.
2. Update `CHANGELOG.md` — move `[Unreleased]` items to the new version section.
3. Commit and push, then tag: `git tag v<version> && git push origin v<version>`.
4. The `release.yaml` workflow builds and uploads the HACS-compatible zip automatically.
