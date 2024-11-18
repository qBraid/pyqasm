# Copyright (C) 2024 qBraid
#
# This file is part of pyqasm
#
# Pyqasm is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for pyqasm, as per Section 15 of the GPL v3.

"""
Module for linear algebra functions necessary for gate decomposition.

"""
from __future__ import annotations

import cmath
import functools
import math
from typing import TYPE_CHECKING

import numpy as np

# pylint: disable-next=no-name-in-module
from pyqasm.accelerate.linalg import so4_to_su2  # type: ignore

if TYPE_CHECKING:
    from numpy.typing import DTypeLike, NDArray


def is_unitary(matrix: np.ndarray, rtol: float = 1e-5, atol: float = 1e-8) -> bool:
    """
    Check if a matrix is unitary.

    A matrix U is unitary if U†U = I, where U† is the conjugate transpose of U.

    Args:
        matrix (np.ndarray): The matrix to check.
        rtol (float): Relative tolerance for numerical stability (default: 1e-5).
        atol (float): Absolute tolerance for numerical stability (default: 1e-8).

    Raises:
        ValueError: If the input is not a numpy array.

    Returns:
        bool: True if the matrix is unitary, False otherwise.
    """
    if not isinstance(matrix, np.ndarray):
        raise ValueError("Input must be a numpy array.")

    if matrix.shape[0] != matrix.shape[1]:
        return False

    identity = np.eye(matrix.shape[0], dtype=matrix.dtype)
    product = np.dot(np.conjugate(matrix.T), matrix)

    return np.allclose(product, identity, rtol=rtol, atol=atol)


def _apply_svd(
    mat: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Helper function to perform SVD on a matrix."""
    if mat.size == 0:
        return np.zeros((0, 0), dtype=mat.dtype), np.array([]), np.zeros((0, 0), dtype=mat.dtype)
    return np.linalg.svd(mat)


def _merge_dtypes(dtype1: DTypeLike, dtype2: DTypeLike) -> np.dtype:
    """Merge two dtypes."""
    return (np.zeros(0, dtype=dtype1) + np.zeros(0, dtype=dtype2)).dtype


def _block_diag(*blocks: NDArray[np.float64]) -> NDArray[np.float64]:
    """Helper function to perform block diagonalization."""
    n = sum(b.shape[0] for b in blocks)
    dtype = functools.reduce(_merge_dtypes, (b.dtype for b in blocks))

    result = np.zeros((n, n), dtype=dtype)
    i = 0
    for b in blocks:
        j = i + b.shape[0]
        result[i:j, i:j] = b
        i = j

    return result


def _orthogonal_diagonalize(
    symmetric_matrix: NDArray[np.float64], diagonal_matrix: NDArray[np.float64]
) -> NDArray[np.float64]:
    """Find orthogonal matrix that diagonalizes symmetric_matrix and diagonal_matrix."""

    def similar_singular(i: int, j: int) -> bool:
        return np.allclose(diagonal_matrix[i, i], diagonal_matrix[j, j])

    ranges = []
    start = 0
    while start < diagonal_matrix.shape[0]:
        past = start + 1
        while past < diagonal_matrix.shape[0] and similar_singular(start, past):
            past += 1
        ranges.append((start, past))
        start = past

    p = np.zeros(symmetric_matrix.shape, dtype=np.float64)
    for start, end in ranges:
        block = symmetric_matrix[start:end, start:end]
        _, res = np.linalg.eigh(block)
        p[start:end, start:end] = res

    return p


# pylint: disable-next=too-many-locals
def orthogonal_bidiagonalize(
    mat1: NDArray[np.float64], mat2: NDArray[np.complex64]
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Find orthogonal matrices that diagonalize mat1 and mat2."""
    atol = 1e-9
    base_left, base_diag, base_right = _apply_svd(mat1)
    base_diag = np.diag(base_diag)

    dim = base_diag.shape[0]
    rank = dim
    while rank > 0 and np.all(np.less_equal(np.abs(base_diag[rank - 1, rank - 1]), atol)):
        rank -= 1
    base_diag = base_diag[:rank, :rank]

    semi_corrected = np.dot(np.dot(base_left.T, np.real(mat2)), base_right.T)

    overlap = semi_corrected[:rank, :rank]
    overlap_adjust = _orthogonal_diagonalize(overlap, base_diag)

    extra = semi_corrected[rank:, rank:]
    extra_left_adjust, _, extra_right_adjust = _apply_svd(extra)

    left_adjust = _block_diag(overlap_adjust, extra_left_adjust)
    right_adjust = _block_diag(overlap_adjust.T, extra_right_adjust)
    left = np.dot(left_adjust.T, base_left.T)
    right = np.dot(base_right.T, right_adjust.T)
    return left, right


def _kak_canonicalize_vector(
    x: float, y: float, z: float
) -> dict[str, tuple[NDArray[np.complex128], NDArray[np.complex128]]]:
    """Canonicalize vector for KAK decomposition."""
    phase = [complex(1)]
    left = [np.eye(2, dtype=np.complex128)] * 2
    right = [np.eye(2, dtype=np.complex128)] * 2
    v = [x, y, z]

    flippers = [
        np.array([[0, 1], [1, 0]]) * 1j,
        np.array([[0, -1j], [1j, 0]]) * 1j,
        np.array([[1, 0], [0, -1]]) * 1j,
    ]

    swappers = [
        np.array([[1, -1j], [1j, -1]]) * 1j * np.sqrt(0.5),
        np.array([[1, 1], [1, -1]]) * 1j * np.sqrt(0.5),
        np.array([[0, 1 - 1j], [1 + 1j, 0]]) * 1j * np.sqrt(0.5),
    ]

    def shift(k: int, step: int) -> None:
        v[k] += step * np.pi / 2
        phase[0] *= 1j**step
        right[0] = np.dot(flippers[k] ** (step % 4), right[0])
        right[1] = np.dot(flippers[k] ** (step % 4), right[1])

    def negate(k1: int, k2: int) -> None:
        v[k1] *= -1
        v[k2] *= -1
        phase[0] *= -1
        s = flippers[3 - k1 - k2]
        left[1] = np.dot(left[1], s)
        right[1] = np.dot(s, right[1])

    def swap(k1: int, k2: int) -> None:
        v[k1], v[k2] = v[k2], v[k1]
        s = swappers[3 - k1 - k2]
        left[0] = np.dot(left[0], s)
        left[1] = np.dot(left[1], s)
        right[0] = np.dot(s, right[0])
        right[1] = np.dot(s, right[1])

    def canonical_shift(k: int) -> None:
        while v[k] <= -np.pi / 4:
            shift(k, +1)
        while v[k] > np.pi / 4:
            shift(k, -1)

    def sort() -> None:
        if abs(v[0]) < abs(v[1]):
            swap(0, 1)
        if abs(v[1]) < abs(v[2]):
            swap(1, 2)
        if abs(v[0]) < abs(v[1]):
            swap(0, 1)

    canonical_shift(0)
    canonical_shift(1)
    canonical_shift(2)
    sort()

    if v[0] < 0:
        negate(0, 2)
    if v[1] < 0:
        negate(1, 2)
    canonical_shift(2)

    atol = 1e-9
    if v[0] > np.pi / 4 - atol and v[2] < 0:
        shift(0, -1)
        negate(0, 2)

    return {
        "single_qubit_operations_after": (left[1], left[0]),
        "single_qubit_operations_before": (right[1], right[0]),
    }


def _deconstruct_matrix_to_angles(
    mat: NDArray[np.floating | np.complexfloating],
) -> tuple[float, float, float]:
    """Breaks down a 2x2 unitary into ZYZ angle parameters."""

    def _phase_matrix(angle: float) -> NDArray[np.complex128]:
        return np.diag([1, np.exp(1j * angle)])

    def _rotation_matrix(angle: float) -> NDArray[np.float64]:
        c, s = np.cos(angle), np.sin(angle)
        return np.array([[c, -s], [s, c]])

    right_phase = cmath.phase(mat[0, 1] * np.conj(mat[0, 0])) + np.pi
    mat = np.dot(mat, _phase_matrix(-right_phase))

    bottom_phase = cmath.phase(mat[1, 0] * np.conj(mat[0, 0]))
    mat = np.dot(_phase_matrix(-bottom_phase), mat)

    rotation = math.atan2(abs(mat[1, 0]), abs(mat[0, 0]))
    mat = np.dot(_rotation_matrix(-rotation), mat)

    diagonal_phase = cmath.phase(mat[1, 1] * np.conj(mat[0, 0]))

    return right_phase + diagonal_phase, rotation * 2, bottom_phase


def so_bidiagonalize(
    mat: NDArray[np.complex128],
) -> tuple[NDArray[np.float64], NDArray[np.complex128], NDArray[np.float64]]:
    """Find special orthogonal L and R so that L @ mat @ R is diagonal."""
    if not is_unitary(mat):
        raise ValueError("Matrix must be unitary.")

    left, right = orthogonal_bidiagonalize(np.real(mat), np.imag(mat))
    with np.errstate(divide="ignore", invalid="ignore"):
        if np.linalg.det(left) < 0:
            left[0, :] *= -1
        if np.linalg.det(right) < 0:
            right[:, 0] *= -1

    diag = functools.reduce(np.dot, (left, mat, right))

    return left, np.diag(diag), right


# pylint: disable-next=too-many-locals
def kak_decomposition_angles(mat: NDArray[np.complex128]) -> list[list[float]]:
    """Decompose matrix into KAK decomposition, return all angles."""
    if not mat.shape == (4, 4) or not is_unitary(mat):
        raise ValueError("Matrix must be 4x4 unitary.")

    kak_magic = np.array([[1, 0, 0, 1j], [0, 1j, 1, 0], [0, 1j, -1, 0], [1, 0, 0, -1j]]) * np.sqrt(
        0.5
    )

    kak_magic_dag = np.conjugate(np.transpose(kak_magic))

    left, d, right = so_bidiagonalize(kak_magic_dag @ mat @ kak_magic)

    a1, a0 = so4_to_su2(left.T)
    b1, b0 = so4_to_su2(right.T)

    kak_gama = np.array([[1, 1, 1, 1], [1, 1, -1, -1], [-1, 1, -1, 1], [1, -1, -1, 1]]) * 0.25

    _, x, y, z = (kak_gama @ np.angle(d).reshape(-1, 1)).flatten()

    inner_cannon = _kak_canonicalize_vector(x, y, z)
    b1 = np.dot(inner_cannon["single_qubit_operations_before"][0], b1)
    b0 = np.dot(inner_cannon["single_qubit_operations_before"][1], b0)
    a1 = np.dot(a1, inner_cannon["single_qubit_operations_after"][0])
    a0 = np.dot(a0, inner_cannon["single_qubit_operations_after"][1])

    pre_phase00, rotation00, post_phase00 = _deconstruct_matrix_to_angles(b1)
    pre_phase01, rotation01, post_phase01 = _deconstruct_matrix_to_angles(b0)
    pre_phase10, rotation10, post_phase10 = _deconstruct_matrix_to_angles(a1)
    pre_phase11, rotation11, post_phase11 = _deconstruct_matrix_to_angles(a0)

    return [
        [rotation00, post_phase00, pre_phase00],
        [rotation01, post_phase01, pre_phase01],
        [rotation10, post_phase10, pre_phase10],
        [rotation11, post_phase11, pre_phase11],
    ]
