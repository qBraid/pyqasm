.. raw:: html

   <html>
   <head>
   <meta name="viewport" content="width=device-width, initial-scale=1">
   <style>
   * {
   box-sizing: border-box;
   }

   body {
   font-family: Arial, Helvetica, sans-serif;
   }

   /* Float four columns side by side */
   .column {
   display: inline-block;
   vertical-align: middle;
   float: none;
   width: 25%;
   padding: 0 10px;
   }

   /* Remove extra left and right margins, due to padding */
   .row {
   text-align: center;
   margin:0 auto;
   }

   /* Clear floats after the columns */
   .row:after {
   content: "";
   display: table;
   clear: both;
   }

   /* Responsive columns */
   @media screen and (max-width: 600px) {
      .column {
         width: 100%;
         margin-bottom: 20px;
      }
   }

   </style>
   </head>
   <body>
   <h1 style="text-align: center">
      <img src="_static/pyqasm.svg" alt="qbraid logo" style="width:60px;height:60px;">
      <span style="color:#808080"> PyQASM</span>
   </h1>
   <p style="text-align:center;font-style:italic;color:#808080">
      Python toolkit for OpenQASM program analysis and compilation.
   </p>
   </body>
   </html>

|

:Release: |release|

Overview
---------

PyQASM is a Python toolkit that providing advanced utilities for semantic analysis and compilation of OpenQASM 3 programs.
Building upon the `OpenQASM 3 parser <https://github.com/openqasm/openqasm>`_, PyQASM offers additional features such as
program validation and unrolling, making it a powerful tool for quantum software developers.

In PyQASM, "unrolling" refers to the process of simplifying a quantum program by expanding custom gate definitions and flattening
complex language constructs like subroutines, loops, and conditional statements into basic operations. This technique, also known as
**program flattening** or **inlining**, transforms nested and recursive structures into a linear sequence of operations consisting solely
of qubit and classical bit declarations, gate operations, and measurement operations. By converting the program into this simplified
format, it becomes easier to perform subsequent transpilation or compilation steps before executing the program on a quantum device.

A practical example of PyQASM's utility is its role in the ``qasm3`` interface of the `qBraid-QIR <https://github.com/qBraid/qbraid-qir>`_
project. Here, PyQASM serves as a core dependency, leveraging its unrolling capabilities to simplify input programs and facilitate their
seamless conversion into Quantum Intermediate Representation (QIR).

Installation
-------------

PyQASM requires Python 3.10 or greater. The base package can be installed with pip as follows:

.. code-block:: bash

   pip install pyqasm


Example
---------

.. code-block:: python

   from pyqasm import loads, dumps

   qasm = """
   OPENQASM 3;
   include "stdgates.inc";

   gate hgate q { h q; }
   gate xgate q { x q; }

   const int[32] N = 4;
   qubit[4] q;
   qubit ancilla;

   def deutsch_jozsa(qubit[N] q_func, qubit[1] ancilla_q) {
      xgate ancilla_q;
      for int i in [0:N-1] { hgate q_func[i]; }
      hgate ancilla_q;
      for int i in [0:N-1] { cx q_func[i], ancilla_q; }
      for int i in [0:N-1] { hgate q_func[i]; }
   }

   deutsch_jozsa(q, ancilla);

   bit[4] result;
   result = measure q;
   """

   program = loads(qasm)
   program.unroll()

   unrolled_qasm = dumps(program)

   print(unrolled_qasm)

.. code-block:: bash

   OPENQASM 3;
   include "stdgates.inc";
   qubit[4] q;
   qubit[1] ancilla;
   x ancilla[0];
   h q[0];
   h q[1];
   h q[2];
   h q[3];
   h ancilla[0];
   cx q[0], ancilla[0];
   cx q[1], ancilla[0];
   cx q[2], ancilla[0];
   cx q[3], ancilla[0];
   h q[0];
   h q[1];
   h q[2];
   h q[3];
   bit[4] result;
   result[0] = measure q[0];
   result[1] = measure q[1];
   result[2] = measure q[2];
   result[3] = measure q[3];

Resources
----------

- `User Guide <https://docs.qbraid.com/pyqasm/user-guide>`_
- `Example Usage <https://github.com/qBraid/pyqasm/tree/main/examples>`_
- `Source Code <https://github.com/qBraid/pyqasm>`_


.. toctree::
   :maxdepth: 1
   :caption: SDK API Reference
   :hidden:

   qbraid <https://sdk.qbraid.com/en/stable/api/qbraid.html>
   qbraid.programs <https://sdk.qbraid.com/en/stable/api/qbraid.programs.html>
   qbraid.interface <https://sdk.qbraid.com/en/stable/api/qbraid.interface.html>
   qbraid.transpiler <https://sdk.qbraid.com/en/stable/api/qbraid.transpiler.html>
   qbraid.passes <https://sdk.qbraid.com/en/stable/api/qbraid.passes.html>
   qbraid.runtime <https://sdk.qbraid.com/en/stable/api/qbraid.runtime.html>
   qbraid.visualization <https://sdk.qbraid.com/en/stable/api/qbraid.visualization.html>

.. toctree::
   :caption: QIR API Reference
   :hidden:

   qbraid_qir <https://sdk.qbraid.com/projects/qir/en/stable/api/qbraid_qir.html>
   qbraid_qir.cirq <https://sdk.qbraid.com/projects/qir/en/stable/api/qbraid_qir.cirq.html>
   qbraid_qir.qasm3 <https://sdk.qbraid.com/projects/qir/en/stable/api/qbraid_qir.qasm3.html>

.. toctree::
   :caption: CORE API Reference
   :hidden:

   qbraid_core <https://sdk.qbraid.com/projects/core/en/stable/api/qbraid_core.html>
   qbraid_core.services <https://sdk.qbraid.com/projects/core/en/stable/api/qbraid_core.services.html>

.. toctree::
   :maxdepth: 1
   :caption: PYQASM API Reference
   :hidden:

   api/pyqasm
