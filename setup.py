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
"""

import os
import subprocess
import sys
import tempfile

import numpy as np
from Cython.Build import cythonize
from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext

# Extensions whose kernels are OpenMP-parallelized.
_OPENMP_EXTENSIONS = {"pyqasm.accelerate.sv_sim"}


def _detect_openmp_unix():
    """Detect OpenMP availability for GCC/Clang and return (compile_args, link_args)."""
    if sys.platform == "darwin" and not os.environ.get("PYQASM_MACOS_OPENMP"):
        # macOS OpenMP needs Homebrew's libomp, whose dylib carries a recent
        # minimum-macOS target. Bundling it into a portable (macosx_11_0) wheel
        # fails `delocate`, so OpenMP is disabled on macOS by default and the
        # sv_sim kernel is built single-threaded. Set PYQASM_MACOS_OPENMP=1 for a
        # local, non-distributed build that has libomp available.
        return [], []

    test_code = b"#include <omp.h>\nint main() { return omp_get_max_threads(); }\n"

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
            cmd = ["cc"] + cflags + ldflags + [tmp_name, "-o", tmp_name + ".out"]
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.unlink(tmp_name + ".out")
            return cflags, ldflags
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            continue
        finally:
            if tmp_name and os.path.exists(tmp_name):
                os.unlink(tmp_name)

    return [], []


class BuildExt(build_ext):
    """Inject portable, compiler-appropriate optimization and OpenMP flags."""

    def build_extensions(self):
        if self.compiler.compiler_type == "msvc":
            base_compile = ["/O2"]
            omp_compile, omp_link = ["/openmp"], []
        else:
            # GCC / Clang on Linux and macOS (and MinGW on Windows).
            base_compile = ["-O3"]
            omp_compile, omp_link = _detect_openmp_unix()
            if omp_compile:
                print(f"OpenMP detected: compile={omp_compile}, link={omp_link}")
            else:
                print("OpenMP not available — building single-threaded kernels")

        for ext in self.extensions:
            ext.extra_compile_args = base_compile + list(ext.extra_compile_args)
            if ext.name in _OPENMP_EXTENSIONS:
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
    ext_modules=cythonize(extensions, language_level=3),
    cmdclass={"build_ext": BuildExt},
)
