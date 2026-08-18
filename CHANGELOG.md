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
- Added an `include_dir` kwarg to `loads()` and `load()`, naming the directory custom `include` statements resolve against. A program given as a string could not resolve includes at all, and failed later naming the gate rather than the include. Resolution is opt-in: without the kwarg, no files are read. ([#368](https://github.com/qBraid/pyqasm/issues/368))

### Improved / Modified

### Deprecated

### Removed

### Fixed
- Fixed an indirect cycle between gate definitions exhausting the Python stack: `gate a q { b q; }` with `gate b q { a q; }` raised a bare `RecursionError` naming nothing, while the direct case was already reported cleanly. The guard compared the body's gate name against one name, so it saw only a cycle of length one. It now tests membership of the whole expansion chain, and names the path: `Recursive definitions not allowed for gate 'a' (a -> b -> a)`. A gate reached twice down separate paths is a diamond, not a cycle, and still expands. ([#369](https://github.com/qBraid/pyqasm/issues/369))
- Fixed a nested external custom gate counting the depth of the decomposition it skipped, the shape the [#352](https://github.com/qBraid/pyqasm/issues/352) fix did not reach: `unroll(external_gates=["outer"])` on a gate whose body calls another custom gate emitted one statement but reported `depth() == 13`. The suppression flag was assigned and cleared without save-restore, so the inner gate clobbered the outer gate's state in both directions. It is now saved and restored, and the depth is recorded once, from the outermost external gate. ([#367](https://github.com/qBraid/pyqasm/issues/367))

### Dependencies

### Other

## Past Release Notes

Archive of changelog entries from previous releases:

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
