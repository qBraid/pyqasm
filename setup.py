"""Build configuration for Cython extensions with optional OpenMP support."""

import os
import platform
import subprocess
import sys
import tempfile

import numpy as np
from Cython.Build import cythonize
from setuptools import Extension, setup

BASE_COMPILE_ARGS = ["-O3", "-ffast-math", "-march=native"]
BASE_LINK_ARGS = []


def _check_openmp():
    """Detect OpenMP availability and return (compile_args, link_args)."""
    test_code = b"#include <omp.h>\nint main() { return omp_get_max_threads(); }\n"

    candidates = []
    if sys.platform == "darwin":
        # macOS: try libomp from Homebrew
        for prefix in ["/opt/homebrew/opt/libomp", "/usr/local/opt/libomp"]:
            if os.path.isdir(prefix):
                candidates.append((
                    ["-Xpreprocessor", "-fopenmp", f"-I{prefix}/include"],
                    [f"-L{prefix}/lib", "-lomp"],
                ))
        # Also try Xcode / system clang with -fopenmp
        candidates.append((["-fopenmp"], ["-fopenmp"]))
    else:
        # Linux / other: standard -fopenmp
        candidates.append((["-fopenmp"], ["-fopenmp"]))

    for cflags, ldflags in candidates:
        try:
            with tempfile.NamedTemporaryFile(suffix=".c", delete=False) as f:
                f.write(test_code)
                f.flush()
                cmd = ["cc"] + cflags + ldflags + [f.name, "-o", f.name + ".out"]
                subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                os.unlink(f.name + ".out")
                os.unlink(f.name)
            return cflags, ldflags
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            try:
                os.unlink(f.name)
            except OSError:
                pass
            continue

    return [], []


omp_cflags, omp_ldflags = _check_openmp()
if omp_cflags:
    print(f"OpenMP detected: compile={omp_cflags}, link={omp_ldflags}")
else:
    print("OpenMP not available — building single-threaded kernels")

sv_sim_compile_args = BASE_COMPILE_ARGS + omp_cflags
sv_sim_link_args = BASE_LINK_ARGS + omp_ldflags

extensions = [
    Extension(
        "pyqasm.accelerate.linalg",
        sources=["src/pyqasm/accelerate/linalg.pyx"],
        include_dirs=[np.get_include()],
        extra_compile_args=BASE_COMPILE_ARGS,
        extra_link_args=BASE_LINK_ARGS,
    ),
    Extension(
        "pyqasm.accelerate.sv_sim",
        sources=["src/pyqasm/accelerate/sv_sim.pyx"],
        include_dirs=[np.get_include()],
        extra_compile_args=sv_sim_compile_args,
        extra_link_args=sv_sim_link_args,
    ),
]

setup(
    ext_modules=cythonize(extensions, language_level=3),
)
