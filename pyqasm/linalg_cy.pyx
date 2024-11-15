# cython: language_level=3
import cython
import numpy as np

DTYPE = np.cdouble

@cython.boundscheck(False)
@cython.wraparound(False)
def kronecker_factor(mat):
    """Split U = kron(A, B) to A and B."""
    cdef Py_ssize_t x_dim = mat.shape[0]
    cdef Py_ssize_t y_dim = mat.shape[1]

    assert x_dim == 4
    assert y_dim == 4
    assert mat.dtype == DTYPE

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

    f1 = np.zeros((2, 2), dtype=DTYPE)
    f2 = np.zeros((2, 2), dtype=DTYPE)

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