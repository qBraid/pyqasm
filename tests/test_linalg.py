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

from pyqasm.linalg import (
    _block_diag,
    _helper_svd,
    _kak_canonicalize_vector,
    _orthogonal_diagonalize,
    _so4_to_su2,
    kak_decomposition_angles,
    orthogonal_bidiagonalize,
)


def test_kak_canonicalize_vector():
    """Test _kak_canonicalize_vector function."""
    x, y, z = -1, -2, -1
    result = _kak_canonicalize_vector(x, y, z)
    assert result["single_qubit_operations_before"][0][0][0] == -np.sqrt(2) / 2 * 1j

    x, y, z = 1, 2, 1
    result = _kak_canonicalize_vector(x, y, z)
    assert result["single_qubit_operations_before"][0][0][0] == -np.sqrt(2) / 2


def test_helper_svd():
    """Test _helper_svd function."""
    mat = np.random.rand(4, 4)
    u, s, vh = _helper_svd(mat)
    assert np.allclose(np.dot(u, np.dot(np.diag(s), vh)), mat)

    mat_empty = np.array([[]])
    u, s, vh = _helper_svd(mat_empty)
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
    a, b = _so4_to_su2(mat)

    assert a.shape == (2, 2)
    assert b.shape == (2, 2)


def test_kak_decomposition_angles():
    """Test KAK decomposition angles."""
    mat = np.eye(4)
    angles = kak_decomposition_angles(mat)

    assert len(angles) == 4
    assert all(len(a) == 3 for a in angles)
