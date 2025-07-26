# Gate Decompositions

This document contains the decomposition diagrams and explanations for various quantum gates implemented in [pyqasm](../src/pyqasm/maps/gates.py).

## [CH Gate](../src/pyqasm/maps/gates.py#L136)

The CH (Controlled-Hadamard) gate is implemented as a decomposition of other gates using the following qiskit decomposition:

```python
In [10]: q = QuantumCircuit(2)

In [11]: q.ch(0, 1)
Out[11]: <qiskit.circuit.instructionset.InstructionSet at 0x127e00a90>

In [12]: q.decompose().draw()
Out[12]:

q_0: ─────────────────■─────────────────────
     ┌───┐┌───┐┌───┐┌─┴─┐┌─────┐┌───┐┌─────┐
q_1: ┤ S ├┤ H ├┤ T ├┤ X ├┤ Tdg ├┤ H ├┤ Sdg ├
     └───┘└───┘└───┘└───┘└─────┘└───┘└─────┘
```

## [XX+YY Gate](../src/pyqasm/maps/gates.py#L168)

The XX+YY gate is implemented using the following qiskit decomposition:

```python
In [7]: qc.draw()
Out[7]:
     ┌─────────────────────┐
q_0: ┤0                    ├
     │  (XX+YY)(theta,phi) │
q_1: ┤1                    ├
     └─────────────────────┘

In [8]: qc.decompose().draw()
Out[8]:
     ┌─────────┐ ┌───┐            ┌───┐┌──────────────┐┌───┐  ┌─────┐   ┌──────────┐
q_0: ┤ Rz(phi) ├─┤ S ├────────────┤ X ├┤ Ry(-theta/2) ├┤ X ├──┤ Sdg ├───┤ Rz(-phi) ├───────────
     ├─────────┴┐├───┴┐┌─────────┐└─┬─┘├──────────────┤└─┬─┘┌─┴─────┴──┐└─┬──────┬─┘┌─────────┐
q_1: ┤ Rz(-π/2) ├┤ √X ├┤ Rz(π/2) ├──■──┤ Ry(-theta/2) ├──■──┤ Rz(-π/2) ├──┤ √Xdg ├──┤ Rz(π/2) ├
     └──────────┘└────┘└─────────┘     └──────────────┘     └──────────┘  └──────┘  └─────────┘
```

## [RYY Gate](../src/pyqasm/maps/gates.py#L201)

The RYY gate is implemented using the following qiskit decomposition:

```python
In [9]: qc.draw()
Out[9]:
     ┌─────────────┐
q_0: ┤0            ├
     │  Ryy(theta) │
q_1: ┤1            ├
     └─────────────┘

In [10]: qc.decompose().draw()
Out[10]:
     ┌─────────┐                       ┌──────────┐
q_0: ┤ Rx(π/2) ├──■─────────────────■──┤ Rx(-π/2) ├
     ├─────────┤┌─┴─┐┌───────────┐┌─┴─┐├──────────┤
q_1: ┤ Rx(π/2) ├┤ X ├┤ Rz(theta) ├┤ X ├┤ Rx(-π/2) ├
     └─────────┘└───┘└───────────┘└───┘└──────────┘
```

## [CRX Gate](../src/pyqasm/maps/gates.py#L307)

The CRX (Controlled-RX) gate is implemented using the following qiskit decomposition:

```python
In [26]: q.draw()
Out[26]:

q_0: ──────■──────
     ┌─────┴─────┐
q_1: ┤ Rx(theta) ├
     └───────────┘

In [27]: q.decompose().decompose().decompose().draw()
Out[27]:

q_0: ────────────────■───────────────────────■───────────────────────
     ┌────────────┐┌─┴─┐┌─────────────────┐┌─┴─┐┌───────────────────┐
q_1: ┤ U(0,0,π/2) ├┤ X ├┤ U(-theta/2,0,0) ├┤ X ├┤ U(theta/2,-π/2,0) ├
     └────────────┘└───┘└─────────────────┘└───┘└───────────────────┘
```

## [CRY Gate](../src/pyqasm/maps/gates.py#L326)

The CRY (Controlled-RY) gate is implemented using the following qiskit decomposition:

```python
In [4]: q.draw()
Out[4]:

q_0: ──────■──────
     ┌─────┴─────┐
q_1: ┤ Ry(theta) ├
     └───────────┘

In [5]: q.decompose().decompose().decompose().draw()
Out[5]:

q_0: ─────────────────────■────────────────────────■──
     ┌─────────────────┐┌─┴─┐┌──────────────────┐┌─┴─┐
q_1: ┤ U3(theta/2,0,0) ├┤ X ├┤ U3(-theta/2,0,0) ├┤ X ├
     └─────────────────┘└───┘└──────────────────┘└───┘
```

## [CRZ Gate](../src/pyqasm/maps/gates.py#L344)

The CRZ (Controlled-RZ) gate is implemented using the following qiskit decomposition:

```python
In [4]: q.draw()
Out[4]:

q_0: ──────■──────
     ┌─────┴─────┐
q_1: ┤ Rz(theta) ├
     └───────────┘

In [5]: q.decompose().decompose().decompose().draw()
Out[5]:
global phase: 0

q_0: ─────────────────────■────────────────────────■──
     ┌─────────────────┐┌─┴─┐┌──────────────────┐┌─┴─┐
q_1: ┤ U3(0,0,theta/2) ├┤ X ├┤ U3(0,0,-theta/2) ├┤ X ├
     └─────────────────┘└───┘└──────────────────┘└───┘
```

## [CU Gate](../src/pyqasm/maps/gates.py#L362)

The CU (Controlled-U) gate is implemented using the following qiskit decomposition:

```python
In [7]: qc.draw()
Out[7]:

q_0: ────────────■─────────────
     ┌───────────┴────────────┐
q_1: ┤ U(theta,phi,lam,gamma) ├
     └────────────────────────┘

In [8]: qc.decompose().decompose().decompose().draw()
Out[8]:
         ┌──────────────┐    ┌──────────────────────┐                                     »
q_0: ────┤ U(0,0,gamma) ├────┤ U(0,0,lam/2 + phi/2) ├──■──────────────────────────────────»
     ┌───┴──────────────┴───┐└──────────────────────┘┌─┴─┐┌──────────────────────────────┐»
q_1: ┤ U(0,0,lam/2 - phi/2) ├────────────────────────┤ X ├┤ U(-theta/2,0,-lam/2 - phi/2) ├»
     └──────────────────────┘                        └───┘└──────────────────────────────┘»
«
«q_0: ──■──────────────────────
«     ┌─┴─┐┌──────────────────┐
«q_1: ┤ X ├┤ U(theta/2,phi,0) ├
«     └───┘└──────────────────┘
```

## [CU3 Gate](../src/pyqasm/maps/gates.py#L389)

The CU3 (Controlled-U3) gate is implemented using the following qiskit decomposition:

```python
In [7]: qc.draw()
Out[7]:

q_0: ──────────■──────────
     ┌─────────┴─────────┐
q_1: ┤ U3(theta,phi,lam) ├
     └───────────────────┘

In [8]: qc.decompose().decompose().decompose().draw()
Out[8]:
     ┌──────────────────────┐
q_0: ┤ U(0,0,lam/2 + phi/2) ├──■────────────────────────────────────■──────────────────────
     ├──────────────────────┤┌─┴─┐┌──────────────────────────────┐┌─┴─┐┌──────────────────┐
q_1: ┤ U(0,0,lam/2 - phi/2) ├┤ X ├┤ U(-theta/2,0,-lam/2 - phi/2) ├┤ X ├┤ U(theta/2,phi,0) ├
     └──────────────────────┘└───┘└──────────────────────────────┘└───┘└──────────────────┘
```

## [CU1 Gate](../src/pyqasm/maps/gates.py#L414)

The CU1 (Controlled-U1) gate is implemented using the following qiskit decomposition:

```python
In [11]: qc.draw()
Out[11]:

q_0: ─■──────────
      │U1(theta)
q_1: ─■──────────

In [12]: qc.decompose().decompose().decompose().draw()
Out[12]:
     ┌────────────────┐
q_0: ┤ U(0,0,theta/2) ├──■───────────────────────■────────────────────
     └────────────────┘┌─┴─┐┌─────────────────┐┌─┴─┐┌────────────────┐
q_1: ──────────────────┤ X ├┤ U(0,0,-theta/2) ├┤ X ├┤ U(0,0,theta/2) ├
                       └───┘└─────────────────┘└───┘└────────────────┘
```

## [CSX Gate](../src/pyqasm/maps/gates.py#L434)

The CSX (Controlled-SX) gate is implemented using the following qiskit decomposition:

```python
In [19]: q = QuantumCircuit(2)

In [20]: q.csx(0,1)
Out[20]: <qiskit.circuit.instructionset.InstructionSet at 0x127e022f0>

In [21]: q.draw()
Out[21]:

q_0: ──■───
     ┌─┴──┐
q_1: ┤ Sx ├
     └────┘

In [22]: q.decompose().decompose().draw()
Out[22]:
         ┌─────────┐
    q_0: ┤ U1(π/4) ├──■────────────────■────────────────────────
         ├─────────┤┌─┴─┐┌──────────┐┌─┴─┐┌─────────┐┌─────────┐
    q_1: ┤ U2(0,π) ├┤ X ├┤ U1(-π/4) ├┤ X ├┤ U1(π/4) ├┤ U2(0,π) ├
         └─────────┘└───┘└──────────┘└───┘└─────────┘└─────────┘
```

## [RZZ Gate](../src/pyqasm/maps/gates.py#L490)

The RZZ gate is implemented using the following qiskit decomposition:

```python
In [32]: q.draw()
Out[32]:

q_0: ─■──────────
      │ZZ(theta)
q_1: ─■──────────

In [33]: q.decompose().decompose().decompose().draw()
Out[33]:
global phase: -theta/2

q_0: ──■─────────────────────■──
     ┌─┴─┐┌───────────────┐┌─┴─┐
q_1: ┤ X ├┤ U3(0,0,theta) ├┤ X ├
     └───┘└───────────────┘└───┘
```

## [CPhaseShift Gate](../src/pyqasm/maps/gates.py#L510)

The controlled phase shift gate is implemented using the following qiskit decomposition:

```python
In [11]: qc.draw()
Out[11]:

q_0: ─■─────────
     │P(theta)
q_1: ─■─────────

In [12]: qc.decompose().decompose().decompose().draw()
Out[12]:
     ┌────────────────┐
q_0: ┤ U(0,0,theta/2) ├──■───────────────────────■────────────────────
     └────────────────┘┌─┴─┐┌─────────────────┐┌─┴─┐┌────────────────┐
q_1: ──────────────────┤ X ├┤ U(0,0,-theta/2) ├┤ X ├┤ U(0,0,theta/2) ├
                       └───┘└─────────────────┘└───┘└────────────────┘
```

## [C3SX Gate](../src/pyqasm/maps/gates.py#L685)

The C3SX (3-Controlled-SX) gate is implemented using the following qiskit decomposition:

```python
In [15]: qc.draw()
Out[15]:

q_0: ──■───
       │
q_1: ──■───
       │
q_2: ──■───
     ┌─┴──┐
q_3: ┤ Sx ├
     └────┘

In [16]: qc.decompose().draw()
Out[16]:

q_0: ──────■──────────■────────────────────■────────────────────────────────────────■────────
           │        ┌─┴─┐                ┌─┴─┐                                      │
q_1: ──────┼────────┤ X ├──────■─────────┤ X ├──────■──────────■────────────────────┼────────
           │        └───┘      │         └───┘      │        ┌─┴─┐                ┌─┴─┐
q_2: ──────┼───────────────────┼────────────────────┼────────┤ X ├──────■─────────┤ X ├──────
     ┌───┐ │U1(π/8) ┌───┐┌───┐ │U1(-π/8) ┌───┐┌───┐ │U1(π/8) ├───┤┌───┐ │U1(-π/8) ├───┤┌───┐
q_3: ┤ H ├─■────────┤ H ├┤ H ├─■─────────┤ H ├┤ H ├─■────────┤ H ├┤ H ├─■─────────┤ H ├┤ H ├─
     └───┘          └───┘└───┘           └───┘└───┘          └───┘└───┘           └───┘└───┘
«
«q_0:─────────────────────────────────■──────────────────────
«                                     │
«q_1:────────────■────────────────────┼──────────────────────
«              ┌─┴─┐                ┌─┴─┐
«q_2:─■────────┤ X ├──────■─────────┤ X ├──────■─────────────
«     │U1(π/8) ├───┤┌───┐ │U1(-π/8) ├───┤┌───┐ │U1(π/8) ┌───┐
«q_3:─■────────┤ H ├┤ H ├─■─────────┤ H ├┤ H ├─■────────┤ H ├
«              └───┘└───┘           └───┘└───┘          └───┘ 