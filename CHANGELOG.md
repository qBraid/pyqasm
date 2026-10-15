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
- The Lab environment from `publish-lab-env.yml` now installs pyqasm with its user-facing extras and ipykernel only. It leaves out the `test`, `lint` and `docs` extras, which added about 50 developer packages, so the environment has 48 packages instead of 100 ([#456](https://github.com/qBraid/pyqasm/pull/456)).
- Named the Lab environments that `publish-lab-env.yml` builds `pyqasm (vX.Y.Z)`, with kernel `Python 3 [pyqasm vX.Y.Z]`, to match the existing pyqasm environments. The rule that keeps a backport from becoming the group's latest reads both this and the older `pyqasm X.Y.Z` name ([#456](https://github.com/qBraid/pyqasm/pull/456)).

### Deprecated

### Removed

### Fixed
- Fixed `loads("")` / whitespace-only input raising `AttributeError` instead of `ValidationError`. Empty and whitespace programs now raise `ValidationError` like other parse failures. ([#451](https://github.com/qBraid/pyqasm/pull/451), [#437](https://github.com/qBraid/pyqasm/issues/437))

### Dependencies

### Other

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
