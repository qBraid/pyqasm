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

### Improved / Modified

### Deprecated

### Removed

### Fixed
- `inv @` and `pow(-n) @` now unroll to the exact inverse of every standard gate. Before, they gave a wrong circuit for `cp00`, `cp01`, `cp10` and their `cphaseshift` aliases, `iswap`, `ms`, `pswap`, `ryy`, `yy`, `xy` and `xx_plus_yy`, and raised on `sx`, `sxdg`, `p`, `u`, `prx`, `gpi`, `gpi2`, `not`, `si`, `ti`, `v`, `vi`, `u1`, `phaseshift`, `rxx`, `rzz`, `xx`, `zz`, `inv @ ctrl @ gphase(...)` and a `gphase` inside an inverted controlled custom gate. `inv @` on `ecr`, `cswap`, `c3x`, `c4x` and `rccx` now emits the reversed decomposition, which is still exact, but its text and its depth next to other gates can differ ([#492](https://github.com/qBraid/pyqasm/pull/492), [#473](https://github.com/qBraid/pyqasm/issues/473), [#476](https://github.com/qBraid/pyqasm/issues/476)).
- `publish-lab-env.yml` files a publish request before it approves the environment. Since qBraid/qbraid-api#1334 the server approves only an environment with an open request, so every run failed at approve with `Environment must have status REQUESTED or PENDING to publish`. The request counts toward the API key owner's publish quota and notifies the platform admins ([#491](https://github.com/qBraid/pyqasm/pull/491), [#490](https://github.com/qBraid/pyqasm/issues/490)).

### Dependencies

### Other

## Past Release Notes

Archive of changelog entries from previous releases:

- [v1.4.0](https://github.com/qBraid/pyqasm/releases/tag/v1.4.0)
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
