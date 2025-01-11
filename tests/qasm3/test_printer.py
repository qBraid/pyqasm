import pytest
from pyqasm.entrypoint import loads, load
from pyqasm.printer import draw

import matplotlib.pyplot as plt
import random
from qbraid import random_circuit, transpile

def _check_fig(circ, fig):
    ax = fig.gca()
    assert len(ax.texts) > 0
    plt.close(fig)

def test_simple():
    qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    bit[2] b;
    h q[0];
    z q[1];
    y q[0];
    rz(pi/1.1) q[0];
    cx q[0], q[1];
    swap q[0], q[1];
    b = measure q;
    """
    circ = loads(qasm)
    fig = circ.draw()
    _check_fig(circ, fig) 
   
def test_random():
    circ = random_circuit("qiskit", measure=random.choice([True, False]))
    qasm_str = transpile(circ, random.choice(["qasm2", "qasm3"]))
    module = loads(qasm_str)
    fig = module.draw()
    _check_fig(circ, fig) 
