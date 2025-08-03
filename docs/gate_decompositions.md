# Gate Decompositions

This document contains the decomposition diagrams and explanations for various quantum gates implemented in [pyqasm](../src/pyqasm/maps/gates.py).

## [U3 Gate](../src/pyqasm/maps/gates.py#L34)

The U3 gate is implemented as a decomposition of other gates using the following qiskit decomposition:

```python
In [10]: q = QuantumCircuit(1)
In [11]: q.u(theta, phi, lam, 0)
In [12]: qc = transpile(q, basis_gates['rz','rx'])
In [13]: print(qc)
Out[14]: 

   ┌────────────┐┌─────────┐┌───────────────┐┌─────────┐┌──────────────┐
q: ┤ Rz(lambda) ├┤ Rx(π/2) ├┤ Rz(theta + π) ├┤ Rx(π/2) ├┤ Rz(phi + 3π) ├
   └────────────┘└─────────┘└───────────────┘└─────────┘└──────────────┘
```

## [CY Gate](../src/pyqasm/maps/gates.py#L129)

The CY (controlled-Y) gate is implemented as a decomposition of other gates using the following qiskit decomposition:

```python
In [10]: q = QuantumCircuit(2)
In [11]: q.cy(0,1)
In [12]: q.decompose().draw()
Out[13]: 
                    
q_0: ─────────■───────
     ┌─────┐┌─┴─┐┌───┐
q_1: ┤ Sdg ├┤ X ├┤ S ├
     └─────┘└───┘└───┘
```

## [CH Gate](../src/pyqasm/maps/gates.py#L144)

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

## [XX+YY Gate](../src/pyqasm/maps/gates.py#L176)

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

## [RYY Gate](../src/pyqasm/maps/gates.py#L209)

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

## [ZZ Gate](../src/pyqasm/maps/gates.py#L230)

The rotation about ZZ axis is implemented as a decomposition of other gates using the following qiskit decomposition:

```python
In [10]: q = QuantumCircuit(2)
In [11]: q.rzz(np.pi,0,1)
In [12]: qc.decompose().draw()  
Out[12]: 
                                                            
q_0: ──■─────────────■──
     ┌─┴─┐┌───────┐┌─┴─┐
q_1: ┤ X ├┤ Rz(π) ├┤ X ├
     └───┘└───────┘└───┘
```

## [Phaseshift Gate](../src/pyqasm/maps/gates.py#L249)

The phaseshift gate is implemented as a decomposition of other gates using the following qiskit decomposition:

```python
In [10]: q = QuantumCircuit(1)
In [11]: q.p(theta,0)
In [12]: new_qc = transpile(q, basis_gates=['rx','h'])
In [13]: print(new_qc)
Out[13]: 

   ┌───┐┌───────────┐┌───┐
q: ┤ H ├┤ Rx(theta) ├┤ H ├
   └───┘└───────────┘└───┘
```

## [CSWAP Gate](../src/pyqasm/maps/gates.py#L264)

The CSWAP (Controlled-SWAP) gate is implemented as a decomposition of other gates using the following qiskit decomposition:

```python
In [10]: q = QuantumCircuit(3)
In [11]: q.cswap(0,1,2)
In [12]: q.decompose().draw()
Out[12]: 
                                                            ┌───┐           
q_0: ────────────────────────■─────────────────────■────■───┤ T ├───■───────
     ┌───┐                   │             ┌───┐   │  ┌─┴─┐┌┴───┴┐┌─┴─┐┌───┐
q_1: ┤ X ├───────■───────────┼─────────■───┤ T ├───┼──┤ X ├┤ Tdg ├┤ X ├┤ X ├
     └─┬─┘┌───┐┌─┴─┐┌─────┐┌─┴─┐┌───┐┌─┴─┐┌┴───┴┐┌─┴─┐├───┤└┬───┬┘└───┘└─┬─┘
q_2: ──■──┤ H ├┤ X ├┤ Tdg ├┤ X ├┤ T ├┤ X ├┤ Tdg ├┤ X ├┤ T ├─┤ H ├────────■──
          └───┘└───┘└─────┘└───┘└───┘└───┘└─────┘└───┘└───┘ └───┘           
```

## [PSWAP Gate](../src/pyqasm/maps/gates.py#L295)

The PSWAP (Phase-SWAP) gate is implemented as a decomposition of other gates using the following qiskit decomposition:

```python
In [10]: pswap_matrix = np.array([[1, 0, 0, 0], 
                                  [0, 0, np.exp(1j * phi), 0], 
                                  [0, np.exp(1j * phi), 0, 0], 
                                  [0, 0, 0, 1]])
In [11]: op = Operator(pswap_matrix)
In [12]: qc = QuantumCircuit(op.num_qubits)
In [13]: qc.append(op.to_instruction(), qc.qubits)
In [14]: qc.decompose().draw()
Out[14]: 

     ┌───────────────┐         ┌──────────────────┐        »
q_0: ┤ U(π/2,-π/2,ϕ) ├──■──────┤ U(π/2,-π/2,-π/2) ├─────■──»
     └──┬──────────┬─┘┌─┴─┐┌───┴──────────────────┴──┐┌─┴─┐»
q_1: ───┤ U(ϕ,ϕ,ϕ) ├──┤ X ├┤ U(1.8581,2.6524,0.4892) ├┤ X ├»
        └──────────┘  └───┘└─────────────────────────┘└───┘»
«              ┌──────────┐             ┌────────────┐
«q_0: ─────────┤ U(ϕ,ϕ,ϕ) ├──────────■──┤ U(π/2,0,ϕ) ├
«     ┌────────┴──────────┴───────┐┌─┴─┐├────────────┤
«q_1: ┤ U(1.1033,0.32306,-2.2097) ├┤ X ├┤ U(π/2,ϕ,0) ├
«     └───────────────────────────┘└───┘└────────────┘
```

## [iSWAP Gate](../src/pyqasm/maps/gates.py#L313)

The iSWAP gate is implemented as a decomposition of other gates using the following qiskit decomposition:

```python
In [10]: q = QuantumCircuit(2)
In [11]: q.iswap(0,1)
In [12]: q.decompose().draw()
Out[12]: 

     ┌───┐┌───┐     ┌───┐     
q_0: ┤ S ├┤ H ├──■──┤ X ├─────
     ├───┤└───┘┌─┴─┐└─┬─┘┌───┐
q_1: ┤ S ├─────┤ X ├──■──┤ H ├
     └───┘     └───┘     └───┘
```

## [CRX Gate](../src/pyqasm/maps/gates.py#L334)

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

## [CRY Gate](../src/pyqasm/maps/gates.py#L353)

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

## [CRZ Gate](../src/pyqasm/maps/gates.py#L371)

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

## [CU Gate](../src/pyqasm/maps/gates.py#L389)

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

## [CU3 Gate](../src/pyqasm/maps/gates.py#L416)

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

## [CU1 Gate](../src/pyqasm/maps/gates.py#L441)

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

## [CSX Gate](../src/pyqasm/maps/gates.py#L461)

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

## [RXX Gate](../src/pyqasm/maps/gates.py#L480)

The RXX gate is implemented using the following qiskit decomposition:

```python
In [10]: q = QuantumCircuit(2)
In [11]: q.rxx(theta,0,1)
In [12]: q.decompose().draw()
Out[12]: 

     ┌───┐                       ┌───┐
q_0: ┤ H ├──■─────────────────■──┤ H ├
     ├───┤┌─┴─┐┌───────────┐┌─┴─┐├───┤
q_1: ┤ H ├┤ X ├┤ Rz(theta) ├┤ X ├┤ H ├
     └───┘└───┘└───────────┘└───┘└───┘

In [13]: q.decompose().decompose().draw()
Out[13]: 

global phase: -theta/2
     ┌─────────┐                       ┌─────────┐
q_0: ┤ U2(0,π) ├──■─────────────────■──┤ U2(0,π) ├
     ├─────────┤┌─┴─┐┌───────────┐┌─┴─┐├─────────┤
q_1: ┤ U2(0,π) ├┤ X ├┤ U1(theta) ├┤ X ├┤ U2(0,π) ├
     └─────────┘└───┘└───────────┘└───┘└─────────┘
```

## [RCCX Gate](../src/pyqasm/maps/gates.py#L504)

The RCCX gate is implemented using the following qiskit decomposition:

```python
In [10]: q = QuantumCircuit(3)
In [11]: q.rccx(0,1,2)
In [12]: q.decompose().draw()
Out[12]: 

                                                                             »
q_0: ─────────────────────────────────────────■──────────────────────────────»
                                              │                              »
q_1: ────────────────────────■────────────────┼───────────────■──────────────»
     ┌─────────┐┌─────────┐┌─┴─┐┌──────────┐┌─┴─┐┌─────────┐┌─┴─┐┌──────────┐»
q_2: ┤ U2(0,π) ├┤ U1(π/4) ├┤ X ├┤ U1(-π/4) ├┤ X ├┤ U1(π/4) ├┤ X ├┤ U1(-π/4) ├»
     └─────────┘└─────────┘└───┘└──────────┘└───┘└─────────┘└───┘└──────────┘»
«                
«q_0: ───────────
«                
«q_1: ───────────
«     ┌─────────┐
«q_2: ┤ U2(0,π) ├
«     └─────────┘
```

## [RZZ Gate](../src/pyqasm/maps/gates.py#L528)

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

## [CPhaseShift Gate](../src/pyqasm/maps/gates.py#L548)

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

## [CPhaseShift00 Gate](../src/pyqasm/maps/gates.py#L568)

The controlled phase shift-00 gate is implemented using the following qiskit decomposition:

```python
In [10]: matrix = np.diag([np.exp(1j * phi), 1.0, 1.0, 1.0])
In [11]: op = Operator(matrix)
In [12]: qc = QuantumCircuit(op.num_qubits)
In [13]: qc.append(op.to_instruction(), qc.qubits)
In [14]: qc.decompose().draw()
Out[14]: 

     ┌──────────────────────┐     ┌──────────────────────┐     »
q_0: ┤ U(0,-2.9717,-1.7407) ├──■──┤ U(π,-0.46112,1.1097) ├──■──»
     └─┬──────────────────┬─┘┌─┴─┐└─────┬──────────┬─────┘┌─┴─┐»
q_1: ──┤ U(0.56139,π/2,0) ├──┤ X ├──────┤ U(ϕ,ϕ,ϕ) ├──────┤ X ├»
       └──────────────────┘  └───┘      └──────────┘      └───┘»
«         ┌──────────┐    
«q_0: ────┤ U(π,ϕ,ϕ) ├────
«     ┌───┴──────────┴───┐
«q_1: ┤ U(1.0094,ϕ,-π/2) ├
«     └──────────────────┘

```

## [CPhaseShift01 Gate](../src/pyqasm/maps/gates.py#L591)

The controlled phase shift-01 gate is implemented using the following qiskit decomposition:

```python
In [10]: matrix = np.diag([1.0, np.exp(1j * phi), 1.0, 1.0])
In [11]: op = Operator(matrix)
In [12]: qc = QuantumCircuit(op.num_qubits)
In [13]: qc.append(op.to_instruction(), qc.qubits)
In [14]: qc.decompose().draw()
Out[14]: 

     ┌──────────────────────┐     ┌──────────────────────┐     »
q_0: ┤ U(0,-2.9717,-1.7407) ├──■──┤ U(π,-0.46112,1.1097) ├──■──»
     └─┬──────────────────┬─┘┌─┴─┐└─────┬──────────┬─────┘┌─┴─┐»
q_1: ──┤ U(2.5802,-π/2,0) ├──┤ X ├──────┤ U(ϕ,ϕ,ϕ) ├──────┤ X ├»
       └──────────────────┘  └───┘      └──────────┘      └───┘»
«         ┌──────────┐   
«q_0: ────┤ U(π,ϕ,ϕ) ├───
«     ┌───┴──────────┴──┐
«q_1: ┤ U(2.1322,ϕ,π/2) ├
«     └─────────────────┘
```

## [CPhaseShift10 Gate](../src/pyqasm/maps/gates.py#L612)

The controlled phase shift-10 gate is implemented using the following qiskit decomposition:

```python
In [10]: matrix = np.diag([1.0, 1.0, np.exp(1j * phi), 1.0])
In [11]: op = Operator(matrix)
In [12]: qc = QuantumCircuit(op.num_qubits)
In [13]: qc.append(op.to_instruction(), qc.qubits)
In [14]: qc.decompose().draw()
Out[14]: 

     ┌──────────────────────┐     ┌──────────────────────┐     »
q_0: ┤ U(0,-2.9717,-1.7407) ├──■──┤ U(π,-0.46112,1.1097) ├──■──»
     └─┬──────────────────┬─┘┌─┴─┐└─────┬──────────┬─────┘┌─┴─┐»
q_1: ──┤ U(2.5802,-π/2,0) ├──┤ X ├──────┤ U(ϕ,ϕ,ϕ) ├──────┤ X ├»
       └──────────────────┘  └───┘      └──────────┘      └───┘»
«         ┌──────────┐   
«q_0: ────┤ U(π,ϕ,ϕ) ├───
«     ┌───┴──────────┴──┐
«q_1: ┤ U(2.1322,ϕ,π/2) ├
«     └─────────────────┘
```

## [ECR Gate](../src/pyqasm/maps/gates.py#L723)

The ECR (Echoed Cross-Resonance) gate is implemented using the following qiskit decomposition:

```python
In [10]: q = QuantumCircuit(2)
In [11]: q.ecr(0,1)
In [12]: q.draw()
Out[12]:

     ┌──────┐
q_0: ┤0     ├
     │  Ecr │
q_1: ┤1     ├
     └──────┘

In [13]: new_qc = transpile(q, basis_gates=['x','cx','rx','s'])
In [14]: new_qc.draw() 
Out[14]: 

        ┌───┐        ┌───┐
q_0: ───┤ S ├─────■──┤ X ├
     ┌──┴───┴──┐┌─┴─┐└───┘
q_1: ┤ Rx(π/2) ├┤ X ├─────
     └─────────┘└───┘     
```

## [C3SX Gate](../src/pyqasm/maps/gates.py#L739)

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
```