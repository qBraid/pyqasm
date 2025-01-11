import pytest
from pyqasm.entrypoint import loads, load
from pyqasm.printer import _draw_mpl

import matplotlib.pyplot as plt
import random
from qbraid import random_circuit, transpile

def test_simple_circuit_drawing():
    qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    bit[2] b;
    h q[0];
    z q[1];
    y q[0];
    rz(pi/0.1) q[0];
    cx q[0], q[1];
    b = measure q;
    """
    
    circuit = loads(qasm)
    fig = _draw_mpl(circuit)
    
    ax = fig.gca()
    plt.savefig("test.png")
    assert len(ax.texts) > 0
    plt.close(fig)
    assert False

@pytest.mark.skip(reason="Not implemented drawing for all gates")
def test_random_qiskit_circuit():
    qiskit_circuit = random_circuit("qiskit", measure=random.choice([True, False]))
    qasm_str = transpile(qiskit_circuit, random.choice(["qasm2", "qasm3"]))
    
    module = load(qasm_str)
    fig = module.draw()
    
    assert isinstance(fig, plt.Figure)
    ax = fig.gca()
    assert len(ax.texts) > 0 
    plt.close(fig)
