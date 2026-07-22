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

# cython: language_level=3
# cython: infer_types=True

import os

import cython

from cython.parallel cimport prange

# OpenMP support is decided purely by compiler flags (-fopenmp / /openmp) in
# setup.py.  Cython emits the OpenMP pragmas for prange behind `#ifdef _OPENMP`
# guards, so the same generated C compiles either way: with OpenMP enabled the
# prange paths parallelize, without it they degrade to serial loops.  Nothing
# here cimports the `openmp` module, so no unguarded <omp.h> is ever pulled in
# and no process-global OpenMP state is mutated at import time.

# Parallelism is opt-in via the PYQASM_NUM_THREADS env var, read once at
# import.  The default is 1 (serial) to avoid conflicts with other OpenMP
# runtimes (e.g. Qiskit Aer) in the same process.  The count is stored in a
# module-level C int and passed explicitly to prange(num_threads=...), so the
# policy does not depend on any per-thread OpenMP internal control variable
# and behaves identically on every Python thread.


def _read_num_threads():
    """Parse PYQASM_NUM_THREADS defensively; malformed or non-positive -> 1."""
    raw = os.environ.get("PYQASM_NUM_THREADS", "1")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 1
    return value if value > 0 else 1


cdef int _NUM_THREADS = _read_num_threads()

# Threshold: parallelize when the statevector has >= this many pairs.
# 2^17 = 131072 pairs corresponds to ~18 qubits (4 MB statevector).
# Below this, OpenMP thread overhead dominates over parallel gains.
cdef Py_ssize_t PARALLEL_THRESHOLD = 131072


# --- cdef kernel functions ---
# Each kernel manages its own GIL release: prange paths use prange's
# built-in nogil, serial paths use explicit `with nogil:` blocks.
# Kernels are noexcept raw-pointer code; ALL argument validation happens in
# the cpdef wrappers below before any pointer is taken.

@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
cdef void _apply_single_qubit_gate(
    double complex* sv,
    Py_ssize_t num_qubits,
    Py_ssize_t target,
    double complex g00,
    double complex g01,
    double complex g10,
    double complex g11,
) noexcept:
    cdef Py_ssize_t half = 1 << (num_qubits - 1)
    cdef Py_ssize_t step = 1 << target
    cdef Py_ssize_t s, i0, i1
    cdef double complex a0, a1

    if _NUM_THREADS > 1 and half >= PARALLEL_THRESHOLD:
        for s in prange(half, schedule='static', num_threads=_NUM_THREADS, nogil=True):
            i0 = ((s >> target) << (target + 1)) | (s & (step - 1))
            i1 = i0 | step
            a0 = sv[i0]
            a1 = sv[i1]
            sv[i0] = g00 * a0 + g01 * a1
            sv[i1] = g10 * a0 + g11 * a1
        return
    with nogil:
        for s in range(half):
            i0 = ((s >> target) << (target + 1)) | (s & (step - 1))
            i1 = i0 | step
            a0 = sv[i0]
            a1 = sv[i1]
            sv[i0] = g00 * a0 + g01 * a1
            sv[i1] = g10 * a0 + g11 * a1


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
cdef void _apply_controlled_gate(
    double complex* sv,
    Py_ssize_t num_qubits,
    Py_ssize_t control,
    Py_ssize_t target,
    double complex g00,
    double complex g01,
    double complex g10,
    double complex g11,
) noexcept:
    cdef Py_ssize_t quarter = 1 << (num_qubits - 2)
    cdef Py_ssize_t lo, hi
    cdef Py_ssize_t lo_mask, hi_limit
    cdef Py_ssize_t s, base, i0, i1
    cdef double complex a0, a1
    cdef Py_ssize_t ctrl_bit = 1 << control
    cdef Py_ssize_t tgt_bit = 1 << target

    if control < target:
        lo = control
        hi = target
    else:
        lo = target
        hi = control

    lo_mask = (1 << lo) - 1
    hi_limit = (1 << hi) - 1

    if _NUM_THREADS > 1 and quarter >= PARALLEL_THRESHOLD:
        for s in prange(quarter, schedule='static', num_threads=_NUM_THREADS, nogil=True):
            base = (s & lo_mask) | (((s >> lo) << (lo + 1)) & hi_limit) | ((s >> (hi - 1)) << (hi + 1))
            base = base | ctrl_bit
            i0 = base
            i1 = base | tgt_bit
            a0 = sv[i0]
            a1 = sv[i1]
            sv[i0] = g00 * a0 + g01 * a1
            sv[i1] = g10 * a0 + g11 * a1
        return
    with nogil:
        for s in range(quarter):
            base = (s & lo_mask) | (((s >> lo) << (lo + 1)) & hi_limit) | ((s >> (hi - 1)) << (hi + 1))
            base = base | ctrl_bit
            i0 = base
            i1 = base | tgt_bit
            a0 = sv[i0]
            a1 = sv[i1]
            sv[i0] = g00 * a0 + g01 * a1
            sv[i1] = g10 * a0 + g11 * a1


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
cdef void _apply_diagonal_gate(
    double complex* sv,
    Py_ssize_t num_qubits,
    Py_ssize_t target,
    double complex phase0,
    double complex phase1,
) noexcept:
    cdef Py_ssize_t half = 1 << (num_qubits - 1)
    cdef Py_ssize_t step = 1 << target
    cdef Py_ssize_t s, i0, i1

    if _NUM_THREADS > 1 and half >= PARALLEL_THRESHOLD:
        for s in prange(half, schedule='static', num_threads=_NUM_THREADS, nogil=True):
            i0 = ((s >> target) << (target + 1)) | (s & (step - 1))
            i1 = i0 | step
            sv[i0] = phase0 * sv[i0]
            sv[i1] = phase1 * sv[i1]
        return
    with nogil:
        for s in range(half):
            i0 = ((s >> target) << (target + 1)) | (s & (step - 1))
            i1 = i0 | step
            sv[i0] = phase0 * sv[i0]
            sv[i1] = phase1 * sv[i1]


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
cdef void _apply_controlled_diagonal_gate(
    double complex* sv,
    Py_ssize_t num_qubits,
    Py_ssize_t control,
    Py_ssize_t target,
    double complex phase,
) noexcept:
    cdef Py_ssize_t quarter = 1 << (num_qubits - 2)
    cdef Py_ssize_t lo, hi
    cdef Py_ssize_t lo_mask, hi_limit
    cdef Py_ssize_t s, base, idx
    cdef Py_ssize_t ctrl_bit = 1 << control
    cdef Py_ssize_t tgt_bit = 1 << target

    if control < target:
        lo = control
        hi = target
    else:
        lo = target
        hi = control

    lo_mask = (1 << lo) - 1
    hi_limit = (1 << hi) - 1

    if _NUM_THREADS > 1 and quarter >= PARALLEL_THRESHOLD:
        for s in prange(quarter, schedule='static', num_threads=_NUM_THREADS, nogil=True):
            base = (s & lo_mask) | (((s >> lo) << (lo + 1)) & hi_limit) | ((s >> (hi - 1)) << (hi + 1))
            idx = base | ctrl_bit | tgt_bit
            sv[idx] = phase * sv[idx]
        return
    with nogil:
        for s in range(quarter):
            base = (s & lo_mask) | (((s >> lo) << (lo + 1)) & hi_limit) | ((s >> (hi - 1)) << (hi + 1))
            idx = base | ctrl_bit | tgt_bit
            sv[idx] = phase * sv[idx]


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
cdef void _apply_two_qubit_gate(
    double complex* sv,
    Py_ssize_t num_qubits,
    Py_ssize_t qubit0,
    Py_ssize_t qubit1,
    double complex* gate,
) noexcept:
    cdef Py_ssize_t quarter = 1 << (num_qubits - 2)
    cdef Py_ssize_t lo, hi
    cdef Py_ssize_t lo_mask, hi_limit
    cdef Py_ssize_t s, base, i00, i01, i10, i11
    cdef double complex a00, a01, a10, a11
    cdef Py_ssize_t q0_bit = 1 << qubit0
    cdef Py_ssize_t q1_bit = 1 << qubit1
    cdef double complex g0 = gate[0], g1 = gate[1], g2 = gate[2], g3 = gate[3]
    cdef double complex g4 = gate[4], g5 = gate[5], g6 = gate[6], g7 = gate[7]
    cdef double complex g8 = gate[8], g9 = gate[9], g10 = gate[10], g11_ = gate[11]
    cdef double complex g12 = gate[12], g13 = gate[13], g14 = gate[14], g15 = gate[15]

    if qubit0 < qubit1:
        lo = qubit0
        hi = qubit1
    else:
        lo = qubit1
        hi = qubit0

    lo_mask = (1 << lo) - 1
    hi_limit = (1 << hi) - 1

    if _NUM_THREADS > 1 and quarter >= PARALLEL_THRESHOLD:
        for s in prange(quarter, schedule='static', num_threads=_NUM_THREADS, nogil=True):
            base = (s & lo_mask) | (((s >> lo) << (lo + 1)) & hi_limit) | ((s >> (hi - 1)) << (hi + 1))
            i00 = base
            i01 = base | q0_bit
            i10 = base | q1_bit
            i11 = base | q0_bit | q1_bit
            a00 = sv[i00]
            a01 = sv[i01]
            a10 = sv[i10]
            a11 = sv[i11]
            sv[i00] = g0 * a00 + g1 * a01 + g2 * a10 + g3 * a11
            sv[i01] = g4 * a00 + g5 * a01 + g6 * a10 + g7 * a11
            sv[i10] = g8 * a00 + g9 * a01 + g10 * a10 + g11_ * a11
            sv[i11] = g12 * a00 + g13 * a01 + g14 * a10 + g15 * a11
        return
    with nogil:
        for s in range(quarter):
            base = (s & lo_mask) | (((s >> lo) << (lo + 1)) & hi_limit) | ((s >> (hi - 1)) << (hi + 1))
            i00 = base
            i01 = base | q0_bit
            i10 = base | q1_bit
            i11 = base | q0_bit | q1_bit
            a00 = sv[i00]
            a01 = sv[i01]
            a10 = sv[i10]
            a11 = sv[i11]
            sv[i00] = g0 * a00 + g1 * a01 + g2 * a10 + g3 * a11
            sv[i01] = g4 * a00 + g5 * a01 + g6 * a10 + g7 * a11
            sv[i10] = g8 * a00 + g9 * a01 + g10 * a10 + g11_ * a11
            sv[i11] = g12 * a00 + g13 * a01 + g14 * a10 + g15 * a11


# --- argument validation ---
# The kernels above are unchecked raw-pointer code, so every cpdef entry point
# validates its arguments first: without this, a malformed call from Python
# segfaults the interpreter instead of raising.

cdef inline void _check_state(double complex[::1] sv, Py_ssize_t num_qubits) except *:
    if num_qubits < 1 or num_qubits > 62:
        raise ValueError(f"num_qubits must be in [1, 62], got {num_qubits}.")
    if sv.shape[0] != (<Py_ssize_t> 1) << num_qubits:
        raise ValueError(
            f"Statevector length {sv.shape[0]} does not match "
            f"2**num_qubits = {(<Py_ssize_t> 1) << num_qubits}."
        )


cdef inline void _check_target(Py_ssize_t num_qubits, Py_ssize_t target) except *:
    if target < 0 or target >= num_qubits:
        raise ValueError(
            f"Target qubit {target} out of range for {num_qubits} qubit(s)."
        )


cdef inline void _check_control_target(
    Py_ssize_t num_qubits, Py_ssize_t control, Py_ssize_t target
) except *:
    _check_target(num_qubits, target)
    if control < 0 or control >= num_qubits:
        raise ValueError(
            f"Control qubit {control} out of range for {num_qubits} qubit(s)."
        )
    if control == target:
        raise ValueError(f"Control and target qubit are both {target}.")


# --- cpdef wrappers for Python API ---

cpdef void apply_single_qubit_gate(
    double complex[::1] sv,
    Py_ssize_t num_qubits,
    Py_ssize_t target,
    double complex[::1] gate,
):
    _check_state(sv, num_qubits)
    _check_target(num_qubits, target)
    if gate.shape[0] < 4:
        raise ValueError(f"Gate buffer must hold 4 elements, got {gate.shape[0]}.")
    cdef double complex* sv_ptr = &sv[0]
    _apply_single_qubit_gate(sv_ptr, num_qubits, target, gate[0], gate[1], gate[2], gate[3])


cpdef void apply_controlled_gate(
    double complex[::1] sv,
    Py_ssize_t num_qubits,
    Py_ssize_t control,
    Py_ssize_t target,
    double complex[::1] gate,
):
    _check_state(sv, num_qubits)
    _check_control_target(num_qubits, control, target)
    if gate.shape[0] < 4:
        raise ValueError(f"Gate buffer must hold 4 elements, got {gate.shape[0]}.")
    cdef double complex* sv_ptr = &sv[0]
    _apply_controlled_gate(sv_ptr, num_qubits, control, target, gate[0], gate[1], gate[2], gate[3])


cpdef void apply_diagonal_gate(
    double complex[::1] sv,
    Py_ssize_t num_qubits,
    Py_ssize_t target,
    double complex phase0,
    double complex phase1,
):
    _check_state(sv, num_qubits)
    _check_target(num_qubits, target)
    cdef double complex* sv_ptr = &sv[0]
    _apply_diagonal_gate(sv_ptr, num_qubits, target, phase0, phase1)


cpdef void apply_controlled_diagonal_gate(
    double complex[::1] sv,
    Py_ssize_t num_qubits,
    Py_ssize_t control,
    Py_ssize_t target,
    double complex phase,
):
    _check_state(sv, num_qubits)
    _check_control_target(num_qubits, control, target)
    cdef double complex* sv_ptr = &sv[0]
    _apply_controlled_diagonal_gate(sv_ptr, num_qubits, control, target, phase)


cpdef void apply_two_qubit_gate(
    double complex[::1] sv,
    Py_ssize_t num_qubits,
    Py_ssize_t qubit0,
    Py_ssize_t qubit1,
    double complex[::1] gate,
):
    _check_state(sv, num_qubits)
    _check_control_target(num_qubits, qubit0, qubit1)
    if gate.shape[0] < 16:
        raise ValueError(f"Gate buffer must hold 16 elements, got {gate.shape[0]}.")
    cdef double complex* sv_ptr = &sv[0]
    cdef double complex* gate_ptr = &gate[0]
    _apply_two_qubit_gate(sv_ptr, num_qubits, qubit0, qubit1, gate_ptr)


# --- Batch dispatch: single Python->C crossing for entire circuit ---

cdef enum OpCode:
    OP_SINGLE = 0
    OP_CONTROLLED = 1
    OP_DIAGONAL = 2
    OP_CTRL_DIAGONAL = 3
    OP_TWO_QUBIT = 4


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
cpdef void apply_circuit(
    double complex[::1] sv,
    Py_ssize_t num_qubits,
    int[::1] opcodes,
    int[::1] targets,
    int[::1] controls,
    double complex[::1] gate_params,
    double complex[::1] diag_phases,
    int[::1] two_qubit_offsets,
    double complex[::1] two_qubit_gates,
    Py_ssize_t n_instructions,
):
    """Execute an entire circuit. Each gate releases the GIL internally.

    All instructions are validated up front (bounds, opcode range, buffer
    sizes) before any kernel touches the statevector, so invalid input raises
    ValueError instead of corrupting memory.
    """
    cdef Py_ssize_t i, gp_offset, dp_offset, tq_offset
    cdef int op, tgt, ctrl

    # --- validation pass (GIL held, O(n_instructions)) ---
    _check_state(sv, num_qubits)
    if n_instructions < 0:
        raise ValueError(f"n_instructions must be >= 0, got {n_instructions}.")
    if (
        opcodes.shape[0] < n_instructions
        or targets.shape[0] < n_instructions
        or controls.shape[0] < n_instructions
        or two_qubit_offsets.shape[0] < n_instructions
    ):
        raise ValueError(
            f"Instruction arrays are shorter than n_instructions = {n_instructions}."
        )
    if gate_params.shape[0] < n_instructions * 4 or diag_phases.shape[0] < n_instructions * 2:
        raise ValueError(
            f"Parameter arrays are shorter than required for "
            f"n_instructions = {n_instructions}."
        )
    for i in range(n_instructions):
        op = opcodes[i]
        tgt = targets[i]
        ctrl = controls[i]
        if op < OP_SINGLE or op > OP_TWO_QUBIT:
            raise ValueError(f"Instruction {i}: invalid opcode {op}.")
        if tgt < 0 or tgt >= num_qubits:
            raise ValueError(
                f"Instruction {i}: target qubit {tgt} out of range for "
                f"{num_qubits} qubit(s)."
            )
        if op == OP_CONTROLLED or op == OP_CTRL_DIAGONAL or op == OP_TWO_QUBIT:
            if ctrl < 0 or ctrl >= num_qubits:
                raise ValueError(
                    f"Instruction {i}: control qubit {ctrl} out of range for "
                    f"{num_qubits} qubit(s)."
                )
            if ctrl == tgt:
                raise ValueError(
                    f"Instruction {i}: control and target qubit are both {tgt}."
                )
        if op == OP_TWO_QUBIT:
            tq_offset = two_qubit_offsets[i]
            if tq_offset < 0 or tq_offset + 16 > two_qubit_gates.shape[0]:
                raise ValueError(
                    f"Instruction {i}: two-qubit gate offset {tq_offset} out of "
                    f"range for buffer of length {two_qubit_gates.shape[0]}."
                )

    # --- dispatch pass ---
    cdef double complex* sv_ptr = &sv[0]
    cdef double complex* gp_ptr = &gate_params[0]
    cdef double complex* dp_ptr = &diag_phases[0]
    cdef double complex* tq_ptr = &two_qubit_gates[0]

    for i in range(n_instructions):
        op = opcodes[i]
        tgt = targets[i]
        ctrl = controls[i]
        gp_offset = i * 4
        dp_offset = i * 2

        if op == OP_SINGLE:
            _apply_single_qubit_gate(
                sv_ptr, num_qubits, tgt,
                gp_ptr[gp_offset], gp_ptr[gp_offset + 1],
                gp_ptr[gp_offset + 2], gp_ptr[gp_offset + 3],
            )
        elif op == OP_CONTROLLED:
            _apply_controlled_gate(
                sv_ptr, num_qubits, ctrl, tgt,
                gp_ptr[gp_offset], gp_ptr[gp_offset + 1],
                gp_ptr[gp_offset + 2], gp_ptr[gp_offset + 3],
            )
        elif op == OP_DIAGONAL:
            _apply_diagonal_gate(
                sv_ptr, num_qubits, tgt,
                dp_ptr[dp_offset], dp_ptr[dp_offset + 1],
            )
        elif op == OP_CTRL_DIAGONAL:
            _apply_controlled_diagonal_gate(
                sv_ptr, num_qubits, ctrl, tgt,
                dp_ptr[dp_offset],
            )
        elif op == OP_TWO_QUBIT:
            tq_offset = two_qubit_offsets[i]
            _apply_two_qubit_gate(
                sv_ptr, num_qubits, ctrl, tgt,
                &tq_ptr[tq_offset],
            )
