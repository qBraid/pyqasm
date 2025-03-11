"""
Sub module for quantum algorithms.

Functions:
----------
    solovay_kitaev: Solovay-Kitaev algorithm for approximating unitary gates.

"""

from pyqasm.algorithms.solovay_kitaev.solovay_kitaev import solovay_kitaev

__all__ = [
    "solovay_kitaev",
]
