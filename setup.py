# Copyright 2025 qBraid
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Build configuration for Cython extensions with optional OpenMP support.

Optimization flags are chosen for portability of the distributed wheels:

  * No ``-march`` (and certainly not ``-march=native``). Wheels are built at the
    baseline ISA so they run on any CPU of the target architecture, matching what
    SciPy and scikit-learn do. ``-march=native`` would tie a wheel to the exact
    CPU of the build machine and can ``SIGILL`` on older hardware.
  * No ``-ffast-math``. The statevector simulator relies on IEEE-754 semantics
    (NaN/Inf handling, no float reassociation), so we keep strict FP.

Flags are also selected per-compiler: ``-O3``/``-fopenmp`` are GCC/Clang
spellings and are silently ignored by MSVC, which needs ``/O2``/``/openmp``.

OpenMP policy per platform:

  * Linux: enabled when the probe succeeds (the norm on manylinux).
  * macOS: disabled by default. There is no portable system libomp, and
    bundling Homebrew's breaks ``delocate``. Set ``PYQASM_MACOS_OPENMP=1`` for
    a local, non-distributed build.
  * Windows: disabled by default. MSVC's ``/openmp`` makes the extension
    depend on ``vcomp140.dll``, which is not part of a stock Windows install;
    ``delvewheel`` then vendors whichever copy it finds first on PATH (on
    GitHub runners that has been ImageMagick's), making releases
    nondeterministic. Set ``PYQASM_WINDOWS_OPENMP=1`` to opt in locally.

OpenMP only affects compiler flags: the generated C guards all OpenMP pragmas
behind ``#ifdef _OPENMP``, so the same sources build serial or parallel and no
flavor is baked into sdists.
"""

import os
import shlex
import subprocess
import sys
import tempfile

import numpy as np
from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext

# Extensions whose kernels are OpenMP-parallelized.
_OPENMP_EXTENSIONS = {"pyqasm.accelerate.sv_sim"}


def _detect_openmp_unix() -> tuple[list[str], list[str]]:
    """Detect OpenMP availability for GCC/Clang.

    Takes no parameters; probes the compiler named by ``$CC`` (or ``cc``) with
    candidate flag sets. Returns ``(compile_args, link_args)`` for the first
    candidate that compiles a test program, or ``([], [])`` when OpenMP is
    unavailable or disabled by platform policy.
    """
    if sys.platform == "darwin" and not os.environ.get("PYQASM_MACOS_OPENMP"):
        return [], []

    test_code = b"#include <omp.h>\nint main() { return omp_get_max_threads(); }\n"

    # Probe with the compiler the build will actually use: honor $CC (which may
    # include flags, e.g. "gcc -pthread") before falling back to plain `cc`.
    compiler_cmd = shlex.split(os.environ.get("CC") or "cc")

    candidates = []
    if sys.platform == "darwin":
        # Opt-in macOS OpenMP: libomp from Homebrew.
        for prefix in ("/opt/homebrew/opt/libomp", "/usr/local/opt/libomp"):
            if os.path.isdir(prefix):
                candidates.append(
                    (
                        ["-Xpreprocessor", "-fopenmp", f"-I{prefix}/include"],
                        [f"-L{prefix}/lib", "-lomp"],
                    )
                )
        # Also try Xcode / system clang with -fopenmp
        candidates.append((["-fopenmp"], ["-fopenmp"]))
    else:
        # Linux / other: standard -fopenmp
        candidates.append((["-fopenmp"], ["-fopenmp"]))

    for cflags, ldflags in candidates:
        tmp_name = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".c", delete=False) as f:
                f.write(test_code)
                f.flush()
                tmp_name = f.name
            cmd = compiler_cmd + cflags + ldflags + [tmp_name, "-o", tmp_name + ".out"]
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.unlink(tmp_name + ".out")
            return cflags, ldflags
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            continue
        finally:
            if tmp_name and os.path.exists(tmp_name):
                os.unlink(tmp_name)

    return [], []


if sys.platform.startswith("win"):
    # MSVC: /openmp is always available but opt-in (see module docstring).
    USE_OPENMP = bool(os.environ.get("PYQASM_WINDOWS_OPENMP"))
    _OMP_COMPILE_UNIX, _OMP_LINK_UNIX = [], []
else:
    _OMP_COMPILE_UNIX, _OMP_LINK_UNIX = _detect_openmp_unix()
    USE_OPENMP = bool(_OMP_COMPILE_UNIX)


class BuildExt(build_ext):
    """Cythonize lazily and inject portable, compiler-appropriate flags.

    Running ``cythonize`` here rather than at module scope keeps the ``.pyx``
    files in ``Extension.sources`` while sdists and wheels are being assembled,
    so generated ``.c`` never ships in release artifacts, and metadata-only
    PEP 517 hooks skip Cython codegen entirely.
    """

    def finalize_options(self) -> None:
        """Cythonize the .pyx extensions in place, then finalize as usual."""
        # pylint: disable-next=import-outside-toplevel
        from Cython.Build import cythonize

        self.distribution.ext_modules[:] = cythonize(
            self.distribution.ext_modules,
            language_level=3,
        )
        super().finalize_options()

    def build_extensions(self) -> None:
        """Apply per-compiler optimization and OpenMP flags, then build."""
        is_msvc = self.compiler.compiler_type == "msvc"
        base_compile = ["/O2"] if is_msvc else ["-O3"]
        if USE_OPENMP:
            omp_compile, omp_link = (
                (["/openmp"], []) if is_msvc else (_OMP_COMPILE_UNIX, _OMP_LINK_UNIX)
            )
            print(f"OpenMP enabled: compile={omp_compile}, link={omp_link}")
        else:
            omp_compile, omp_link = [], []
            print("OpenMP disabled - building single-threaded kernels")

        for ext in self.extensions:
            ext.extra_compile_args = base_compile + list(ext.extra_compile_args)
            if ext.name in _OPENMP_EXTENSIONS and USE_OPENMP:
                ext.extra_compile_args += omp_compile
                ext.extra_link_args = list(ext.extra_link_args) + omp_link

        super().build_extensions()


extensions = [
    Extension(
        "pyqasm.accelerate.linalg",
        sources=["src/pyqasm/accelerate/linalg.pyx"],
        include_dirs=[np.get_include()],
    ),
    Extension(
        "pyqasm.accelerate.sv_sim",
        sources=["src/pyqasm/accelerate/sv_sim.pyx"],
        include_dirs=[np.get_include()],
    ),
]

setup(
    ext_modules=extensions,
    cmdclass={"build_ext": BuildExt},
)
