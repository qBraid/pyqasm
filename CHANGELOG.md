# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Types of changes:
- `Added`: for new features.
- `Improved`: for improvements to existing functionality.
- `Deprecated`: for soon-to-be removed features.
- `Removed`: for now removed features.
- `Fixed`: for any bug fixes.
- `Dependencies`: for updates to external libraries or packages.

## Unreleased

### Added
- Added the `Publish qBraid Lab environment` workflow (`publish-lab-env.yml`), run by hand for a released version. It builds an environment with pyqasm and every extra it declares on an Ubuntu 24.04 runner with the system Python 3.12, which matches Lab, and smoke tests it. Then it uploads and approves it on qBraid staging or production, and adds it to the configured group as its latest. A failed run can resume from its slug. Each target reads its API key and URL from the `env-publish-staging` or `env-publish-production` GitHub Environment. The steps live in `bin/publish_lab_env.py` and `bin/lab_env_smoke_test.py` ([#455](https://github.com/qBraid/pyqasm/pull/455)).

### Improved / Modified
- **Breaking:** circuit drawing moved from `pyqasm.printer` to `pyqasm.visualization`. `pyqasm.draw` is unchanged, but code that imports from `pyqasm.printer`, such as `from pyqasm.printer import mpl_draw`, must import from `pyqasm.visualization` instead ([#461](https://github.com/qBraid/pyqasm/pull/461)).
- `publish-lab-env.yml` sets the pyqasm light and dark logos from qbraid-static-assets as the environment's catalog logo and kernel icon. An optional `QBRAID_ENV_LOGO_URL` variable, the https URL of a PNG, overrides both. It replaces `QBRAID_ENV_LOGO`, since pyqasm is not a qBraid provider ([#456](https://github.com/qBraid/pyqasm/pull/456)).
- The Lab environment from `publish-lab-env.yml` now installs pyqasm with its user-facing extras and ipykernel only. It leaves out the `test`, `lint` and `docs` extras, which added about 50 developer packages, so the environment has 48 packages instead of 100 ([#456](https://github.com/qBraid/pyqasm/pull/456)).
- Named the Lab environments that `publish-lab-env.yml` builds `pyqasm (vX.Y.Z)`, with kernel `Python 3 [pyqasm vX.Y.Z]`, to match the existing pyqasm environments. The rule that keeps a backport from becoming the group's latest reads both this and the older `pyqasm X.Y.Z` name ([#456](https://github.com/qBraid/pyqasm/pull/456)).

### Deprecated

### Removed

### Fixed
- `loads()` syntax errors now name the offending token, line and column, e.g. `Failed to parse OpenQASM string: syntax error near ';' at line 3, column 13`. Before, the reason after the colon was empty ([#460](https://github.com/qBraid/pyqasm/pull/460)).
- Fixed the matplotlib printer's controlled-gate lookup for `c3x` and `c4x` ([#458](https://github.com/qBraid/pyqasm/pull/458), [#322](https://github.com/qBraid/pyqasm/issues/322)).
- Fixed `loads("")` / whitespace-only input raising `AttributeError` instead of `ValidationError`. Empty and whitespace programs now raise `ValidationError` like other parse failures. ([#451](https://github.com/qBraid/pyqasm/pull/451), [#437](https://github.com/qBraid/pyqasm/issues/437))

### Dependencies
- Bumped `github/codeql-action/upload-sarif` from 3.37.8 to 4.38.1. ([#431](https://github.com/qBraid/pyqasm/pull/431))
- Bumped `actions/upload-artifact` from 4.6.2 to 7.0.2 in `scorecard.yml`, and pinned the other workflows to 7.0.2 instead of the `v7` major tag. ([#453](https://github.com/qBraid/pyqasm/pull/453))
- Bumped `ossf/scorecard-action` from 2.4.4 to 2.5.0. ([#457](https://github.com/qBraid/pyqasm/pull/457))

### Other
- `lab-env-tools.in` sets minimum versions for qbraid-cli and qbraid-core instead of exact ones, so Dependabot's weekly `uv` update can raise them together. Its exact pins made that update fail. `lab-env-tools.txt` still installs qbraid-cli 0.16.10 and qbraid-core 0.6.27 ([#465](https://github.com/qBraid/pyqasm/pull/465)).
- Hardened the GitHub Actions workflows for the OpenSSF Scorecard and CodeQL alerts. Every action is pinned to a commit SHA. Every workflow declares least-privilege `GITHUB_TOKEN` permissions. Workflow tools install from hash-locked files in `.github/requirements/`. A grouped weekly Dependabot PR updates them. The `pr-compliance.yml` job no longer checks out the repository ([#463](https://github.com/qBraid/pyqasm/pull/463)).

## Past Release Notes

Archive of changelog entries from previous releases:

- [v1.3.0](https://github.com/qBraid/pyqasm/releases/tag/v1.3.0)
- [v1.2.1](https://github.com/qBraid/pyqasm/releases/tag/v1.2.1)
- [v1.2.0](https://github.com/qBraid/pyqasm/releases/tag/v1.2.0)
- [v1.1.0](https://github.com/qBraid/pyqasm/releases/tag/v1.1.0)
- [v1.0.4](https://github.com/qBraid/pyqasm/releases/tag/v1.0.4)
- [v1.0.3](https://github.com/qBraid/pyqasm/releases/tag/v1.0.3)
- [v1.0.2](https://github.com/qBraid/pyqasm/releases/tag/v1.0.2)
- [v1.0.1](https://github.com/qBraid/pyqasm/releases/tag/v1.0.1)
- [v1.0.0](https://github.com/qBraid/pyqasm/releases/tag/v1.0.0)
- [v0.5.0](https://github.com/qBraid/pyqasm/releases/tag/v0.5.0)
- [v0.4.0](https://github.com/qBraid/pyqasm/releases/tag/v0.4.0)
- [v0.3.2](https://github.com/qBraid/pyqasm/releases/tag/v0.3.2)
- [v0.3.1](https://github.com/qBraid/pyqasm/releases/tag/v0.3.1)
- [v0.3.0](https://github.com/qBraid/pyqasm/releases/tag/v0.3.0)
- [v0.2.1](https://github.com/qBraid/pyqasm/releases/tag/v0.2.1)
- [v0.2.0](https://github.com/qBraid/pyqasm/releases/tag/v0.2.0)
- [v0.1.0](https://github.com/qBraid/pyqasm/releases/tag/v0.1.0)
- [v0.1.0-alpha](https://github.com/qBraid/pyqasm/releases/tag/v0.1.0-alpha)
- [v0.0.3](https://github.com/qBraid/pyqasm/releases/tag/v0.0.3)
- [v0.0.2](https://github.com/qBraid/pyqasm/releases/tag/v0.0.2)
- [v0.0.1](https://github.com/qBraid/pyqasm/releases/tag/v0.0.1)
