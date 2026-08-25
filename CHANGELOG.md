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
- Fixed `pyqasm validate` wrapping its diagnostics at the console width, which split a file path longer than the width across lines mid-token and left it neither copyable nor clickable. The error console now uses `soft_wrap`, keeping one diagnostic per line.
- Fixed an indirect cycle between gate definitions exhausting the Python stack: `gate a q { b q; }` with `gate b q { a q; }` raised a bare `RecursionError` naming nothing, while the direct case was already reported cleanly. The guard compared the body's gate name against one name, so it saw only a cycle of length one. It now tests membership of the whole expansion chain, and names the path: `Recursive definitions not allowed for gate 'a' (a -> b -> a)`. A gate reached twice down separate paths is a diamond, not a cycle, and still expands. ([#369](https://github.com/qBraid/pyqasm/issues/369))
- Fixed a nested external custom gate counting the depth of the decomposition it skipped, the shape the [#352](https://github.com/qBraid/pyqasm/issues/352) fix did not reach: `unroll(external_gates=["outer"])` on a gate whose body calls another custom gate emitted one statement but reported `depth() == 13`. The suppression flag was assigned and cleared without save-restore, so the inner gate clobbered the outer gate's state in both directions. It is now saved and restored, and the depth is recorded once, from the outermost external gate. ([#367](https://github.com/qBraid/pyqasm/issues/367))

### Dependencies

### Other
- Fixed the pre-release workflow publishing its source distribution under the released version instead of the pre-release one. `build_sdist.sh` ran `git reset --hard` and `git clean -xdf`, which discarded the `pyproject.toml` version that the preceding step had just stamped, so a run that built `1.1.0a0` wheels built a `1.1.0` sdist and PyPI rejected it as a duplicate. `pre_build.sh` already resets the tree, so the second reset is gone. It also no longer destroys uncommitted work when the script is run locally. ([#413](https://github.com/qBraid/pyqasm/pull/413))
- Added a `SECURITY.md` with a private vulnerability disclosure path. There was no documented way to report one, leaving a public issue or a guessed email address as the only options. Reports now go through this repository's GitHub security advisory form. ([#383](https://github.com/qBraid/pyqasm/pull/383))

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
