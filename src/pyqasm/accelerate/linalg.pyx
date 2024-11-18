# Copyright (C) 2024 qBraid
#
# This file is part of pyqasm
#
# Pyqasm is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for pyqasm, as per Section 15 of the GPL v3.

# cython: language_level=3
# cython: infer_types=True
import cython
import numpy as np

ctypedef fused RealorComplexDouble:
    double
    double complex


@cython.boundscheck(False)
@cython.wraparound(False)
cdef _kronecker_factor(double complex[:, ::1] mat):
    cdef Py_ssize_t x_dim = mat.shape[0]
    cdef Py_ssize_t y_dim = mat.shape[1]

    assert x_dim == y_dim == 4

    cdef Py_ssize_t a = 0, b = 0
    cdef double max_abs = 0.0
    cdef double abs_val
    cdef Py_ssize_t i, j

    for i in range(4):
        for j in range(4):
            abs_val = abs(mat[i, j])
            if abs_val > max_abs:
                max_abs = abs_val
                a, b = i, j

    f1 = np.zeros((2, 2), dtype=np.cdouble)
    f2 = np.zeros((2, 2), dtype=np.cdouble)

    for i in range(2):
        for j in range(2):
            f1[(a >> 1) ^ i, (b >> 1) ^ j] = mat[a ^ (i << 1), b ^ (j << 1)]
            f2[(a & 1) ^ i, (b & 1) ^ j] = mat[a ^ i, b ^ j]

    cdef double complex det_f1, det_f2, g
    with np.errstate(divide="ignore", invalid="ignore"):
        det_f1 = np.sqrt(np.linalg.det(f1)) or np.cdouble(1)
        det_f2 = np.sqrt(np.linalg.det(f2)) or np.cdouble(1)
        f1 /= det_f1
        f2 /= det_f2

    g = mat[a, b] / (f1[a >> 1, b >> 1] * f2[a & 1, b & 1])
    if g.real < 0:
        f1 *= -1
        g *= -1

    return g, f1, f2


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef kronecker_factor(double complex[:, ::1] mat):
    return _kronecker_factor(mat)


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef so4_to_su2(RealorComplexDouble[:, :] mat):
    cdef double complex[:, ::1] magic, ab
    cdef double complex[:, :] magic_conj_t, a, b
    magic = np.array(
        [
            [1, 0, 0, 1j],
            [0, 1j, 1, 0],
            [0, 1j, -1, 0],
            [1, 0, 0, -1j],
        ],
        dtype=np.cdouble,
    ) * np.sqrt(0.5)

    magic_conj_t = np.conj(magic.T)

    ab = np.dot(np.dot(magic, mat), magic_conj_t)
    _, a, b = _kronecker_factor(ab)

    return a, b
