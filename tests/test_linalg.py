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
Module containing unit tests for linalg.py functions.

"""
import numpy as np
import pytest

# pylint: disable-next=no-name-in-module
from pyqasm.accelerate.linalg import kronecker_factor, so4_to_su2  # type: ignore
from pyqasm.linalg import (
    _apply_svd,
    _block_diag,
    _deconstruct_matrix_to_angles,
    _kak_canonicalize_vector,
    _orthogonal_diagonalize,
    is_unitary,
    kak_decomposition_angles,
    orthogonal_bidiagonalize,
    so_bidiagonalize,
)


def test_kak_canonicalize_vector():
    """Test _kak_canonicalize_vector function."""
    x, y, z = -1, -2, -1
    result = _kak_canonicalize_vector(x, y, z)
    assert result["single_qubit_operations_before"][0][0][0] == -np.sqrt(2) / 2 * 1j

    x, y, z = 1, 2, 1
    result = _kak_canonicalize_vector(x, y, z)
    assert result["single_qubit_operations_before"][0][0][0] == -np.sqrt(2) / 2


@pytest.mark.parametrize(
    "x,y,z",
    [
        (0.1, 0.2, 0.3),
        (0.3, 0.2, 0.1),
        (-0.1, -0.2, -0.3),
        (np.pi / 4, 0, 0),
        (0, np.pi / 4, 0),
        (0, 0, np.pi / 4),
        (np.pi / 3, 0.2, -0.1),
        (np.pi / 5, 0.2, 0.1),
        (np.pi / 4 + 1e-9, 0, -1),
    ],
)
def test_kak_canonicalize_vector_general(x, y, z):
    result = _kak_canonicalize_vector(x, y, z)
    assert "single_qubit_operations_after" in result
    assert "single_qubit_operations_before" in result
    assert all(op.shape == (2, 2) for op in result["single_qubit_operations_after"])
    assert all(op.shape == (2, 2) for op in result["single_qubit_operations_before"])


@pytest.mark.parametrize(
    "x,y,z",
    [
        (0, 0, 0),
        (np.pi / 4, np.pi / 4, np.pi / 4),
        (-np.pi / 4, -np.pi / 4, -np.pi / 4),
    ],
)
def test_kak_canonicalize_vector_edge_cases(x, y, z):
    result = _kak_canonicalize_vector(x, y, z)
    assert "single_qubit_operations_after" in result
    assert "single_qubit_operations_before" in result


def test_apply_svd():
    """Test _apply_svd function."""
    mat = np.random.rand(4, 4)
    u, s, vh = _apply_svd(mat)
    assert np.allclose(np.dot(u, np.dot(np.diag(s), vh)), mat)

    mat_empty = np.array([[]])
    u, s, vh = _apply_svd(mat_empty)
    assert u.shape == (0, 0)
    assert vh.shape == (0, 0)
    assert len(s) == 0


def test_block_diag():
    """Test block diagonalization of matrices."""
    a = np.random.rand(2, 2)
    b = np.random.rand(3, 3)
    res = _block_diag(a, b)

    assert res.shape == (5, 5)
    assert np.allclose(res[:2, :2], a)
    assert np.allclose(res[2:, 2:], b)


def test_orthogonal_diagonalize():
    """Test orthogonal diagonalization of matrices."""
    mat1 = np.eye(3)
    mat2 = np.diag([1, 2, 3])
    p = _orthogonal_diagonalize(mat1, mat2)

    assert np.allclose(np.dot(p.T, np.dot(mat1, p)), np.eye(3))


def test_orthogonal_bidiagonalize():
    """Test orthogonal bidiagonalization of matrices."""
    mat1 = np.random.rand(4, 4)
    mat2 = np.random.rand(4, 4)
    left, right = orthogonal_bidiagonalize(mat1, mat2)

    assert left.shape == (4, 4)
    assert right.shape == (4, 4)


def test_so4_to_su2():
    """Test SO4 to SU2 conversion."""
    mat = np.eye(4)
    a, b = so4_to_su2(mat)

    assert a.shape == (2, 2)
    assert b.shape == (2, 2)


def test_kak_decomposition_angles():
    """Test KAK decomposition angles."""
    mat = np.eye(4)
    angles = kak_decomposition_angles(mat)

    assert len(angles) == 4
    assert all(len(a) == 3 for a in angles)


def test_kronecker_fator():
    """Test _kronecker_fator function."""
    a = np.array([[1, 2], [3, 4]], dtype=np.complex128)
    b = np.array([[0, 5], [6, 7]], dtype=np.complex128)
    mat = np.kron(a, b)

    g, f1, f2 = kronecker_factor(mat)

    assert np.allclose(g * np.kron(f1, f2), mat)
    assert f1.shape == (2, 2)
    assert f2.shape == (2, 2)


def test_deconstruct_matrix_to_angles():
    """Test _deconstruct_matrix_to_angles function."""
    mat = np.array([[1, 0], [0, 1j]])
    angles = _deconstruct_matrix_to_angles(mat)

    assert len(angles) == 3
    assert all(isinstance(angle, float) for angle in angles)


def test_so_bidiagonalize_unitary():
    """Test so_bidiagonalize function with a unitary matrix."""
    mat = np.array([[1 / np.sqrt(2), 1 / np.sqrt(2)], [1j / np.sqrt(2), -1j / np.sqrt(2)]])
    left, diag, right = so_bidiagonalize(mat)

    assert left.shape == (2, 2)
    assert right.shape == (2, 2)
    assert diag.shape == (2,)

    assert np.allclose(left @ mat @ right, np.diag(diag))


def test_so_bidiagonalize_raises_for_non_unitary():
    """Test so_bidiagonalize function raises ValueError for non-unitary matrix."""
    mat = np.array([[1, 2j], [-2j, 3]])
    with pytest.raises(ValueError, match="Matrix must be unitary"):
        so_bidiagonalize(mat)


def test_so_bidiagonalize_right_neg_det():
    """Test so_bidiagonalize with a matrix that triggers right determinant adjustment."""
    mat = np.array(
        [[1 / np.sqrt(2), 1j / np.sqrt(2)], [1j / np.sqrt(2), 1 / np.sqrt(2)]], dtype=np.complex128
    )

    assert is_unitary(mat)

    left, diag, right = so_bidiagonalize(mat)
    assert np.linalg.det(right) >= 0

    reconstructed = np.dot(left, np.dot(mat, right))
    assert np.allclose(reconstructed, np.diag(diag), atol=1e-8)


@pytest.mark.parametrize(
    "mat",
    [
        np.array(
            [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16]]
        ),  # 4x4 matrix, but not unitary
        np.array(
            [[1 / np.sqrt(2), 1 / np.sqrt(2)], [1j / np.sqrt(2), -1j / np.sqrt(2)]]
        ),  # Unitary matrix, but not 4x4
    ],
)
def test_kak_decomp_raises_for_invalid_mat(mat):
    """Test kak_decomposition_angles raises ValueError for non-unitary or non-4x4 matrix."""
    with pytest.raises(ValueError, match="Matrix must be 4x4 unitary."):
        kak_decomposition_angles(mat)


@pytest.mark.parametrize(
    "matrix,expected",
    [
        (np.array([[1, 0], [0, -1]]), True),
        (np.array([[1 / np.sqrt(2), 1 / np.sqrt(2)], [1 / np.sqrt(2), -1 / np.sqrt(2)]]), True),
        (np.array([[1, 1], [1, 1]]), False),
        (np.array([[1, 0], [0, 1], [1, 0]]), False),
        (np.array([[1 + 1j, 0], [0, 1 - 1j]]) / np.sqrt(2), True),
    ],
)
def test_is_unitary(matrix, expected):
    """Test is_unitary function with various matrices."""
    assert is_unitary(matrix) == expected


@pytest.mark.parametrize(
    "matrix,rtol,atol,expected",
    [
        (np.eye(2) + 1e-6, 1e-5, 1e-8, False),
        (np.eye(2) + 1e-6, 1e-4, 1e-5, True),
    ],
)
def test_is_unitary_with_tolerances(matrix, rtol, atol, expected):
    """Test is_unitary function with tolerances."""
    assert is_unitary(matrix, rtol=rtol, atol=atol) == expected


@pytest.mark.parametrize("matrix", ["not a matrix", 123])
def test_is_unitary_invalid_input(matrix):
    """Test is_unitary function raises ValueError for invalid input."""
    with pytest.raises(ValueError):
        is_unitary(matrix)
