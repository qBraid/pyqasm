import math
from typing import List
import numpy as np
from pyqasm.algorithms.solovay_kitaev.utils import SU2Matrix

def u_to_bloch(u):
  """Compute angle and axis for a unitary."""

  angle = np.real(np.arccos((u[0, 0] + u[1, 1]) / 2))
  sin = np.sin(angle)
  if sin < 1e-10:
    axis = [0, 0, 1]
  else:
    nx = (u[0, 1] + u[1, 0]) / (2j * sin)
    ny = (u[0, 1] - u[1, 0]) / (2 * sin)
    nz = (u[0, 0] - u[1, 1]) / (2j * sin)
    axis = [nx, ny, nz]
  return axis, 2 * angle

def Rotation(vparm: List[float], theta: float, name: str):
  """Produce the single-qubit rotation operator."""

  v = np.asarray(vparm)
  if v.shape != (3,) or not math.isclose(v @ v, 1) or not np.all(np.isreal(v)):
    raise ValueError('Rotation vector v must be a 3D real unit vector.')

  return np.cos(theta / 2) * np.identity(2) - 1j * np.sin(theta / 2) * (v[0] * np.array([[0.0, 1.0], [1.0, 0.0]]) + v[1] * np.array([[0.0, -1.0j], [1.0j, 0.0]]) + v[2] * np.array([[1.0, 0.0], [0.0, -1.0]]))


def RotationX(theta: float):
  return Rotation([1.0, 0.0, 0.0], theta, 'Rx')


def RotationY(theta: float):
  return Rotation([0.0, 1.0, 0.0], theta, 'Ry')


def RotationZ(theta: float):
  return Rotation([0.0, 0.0, 1.0], theta, 'Rz')

def gc_decomp(u):
    axis, theta = u_to_bloch(u)
    
    phi = 2.0 * np.arcsin(np.sqrt(np.sqrt((0.5 - 0.5 * np.cos(theta / 2)))))
    v = RotationX(phi)
    if axis[2] > 0:
        w = RotationY(2 * np.pi - phi)
    else:
        w = RotationY(phi)
    
    _, ud = np.linalg.eig(u)
    
    vwvdwd = v @ w @ v.conj().T @ w.conj().T
    
    s = ud @ vwvdwd.conj().T

    v_hat = s @ v @ s.conj().T
    w_hat = s @ w @ s.conj().T
    return SU2Matrix(v_hat, []), SU2Matrix(w_hat, [])