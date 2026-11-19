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
- `/` between integer operands, meaning integer literals and `int` or `uint` variables, is now integer division, truncated toward zero, as the spec defines (`b / a; // 1`). This also changes angles: `rx(1 / 2)` is now `rx(0)`, was `rx(0.5)`, `rx(3 / 4 * pi)` is now `rx(0.0)`, was `rx(2.356194490192345)`, and with `int[32] a = 2; int[32] b = 3;`, `rx(b / a)` is now `rx(1)`, was `rx(1.5)`. Gate parameters are angles and keep real division (`g(3)` with `rx(t / 2)` in the body is still `rx(1.5)`). OpenQASM 2 has no integer type, so its programs keep real division, also after `to_qasm3()`, which writes `1/2` as `1.0 / 2.0` ([#474](https://github.com/qBraid/pyqasm/pull/474)).
- `unroll()` accepts `inv @` on a custom gate whose body contains `nop`, and keeps each `nop` in the inverted body. Before, it raised `ValidationError: Unsupported / undeclared QASM operation: nop` ([#485](https://github.com/qBraid/pyqasm/pull/485), [#477](https://github.com/qBraid/pyqasm/issues/477)).
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
