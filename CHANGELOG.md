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
- Added support to `OPENPULSE` code in pyqasm. ([#246](https://github.com/qBraid/pyqasm/pull/246))
  ###### Example:
  ```qasm
  OPENQASM 3.0;
  defcalgrammar "openpulse";
    
  complex[float[32]] amp = 1.0 + 2.0im;
  cal {
      port d0;
      frame driveframe = newframe(d0, 5.0e9, 0.0);
      waveform wf = gaussian(amp, 16ns, 4ns);
  }
    
  const float frequency_start = 4.5e9;
  const float frequency_step = 1e6;
  const int frequency_num_steps = 3;
  
  defcal saturation_pulse $0 {
      play(driveframe, constant(amp, 100e-6s));
  }
    
  cal {
      set_frequency(driveframe, frequency_start);
  }
    
  for int i in [1:frequency_num_steps] {
      cal {
          shift_frequency(driveframe, frequency_step);
      }
      saturation_pulse $0;
  }
  ```
- Added a workflow to track changes in the `docs/_static/logo.png` file to prevent unnecessary modifications. ([#257](https://github.com/qBraid/pyqasm/pull/257))

### Improved / Modified
- Modified if statement validation to now include empty blocks as well. See [Issue #246](https://github.com/qBraid/pyqasm/issues/246) for details. ([#251](https://github.com/qBraid/pyqasm/pull/251))

### Deprecated

### Removed

### Fixed
- Fixed Complex value initialization error. ([#253](https://github.com/qBraid/pyqasm/pull/253))
- Fixed duplicate qubit argument check in function calls and  Error in function call with aliased qubit. ([#260](https://github.com/qBraid/pyqasm/pull/260))


### Dependencies
- Bumps `@actions/checkout` from 4 to 5 ([#250](https://github.com/qBraid/pyqasm/pull/250))

### Other

## Past Release Notes

Archive of changelog entries from previous releases:

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
