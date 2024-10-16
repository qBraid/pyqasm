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
      <img src="_static/logo.png" alt="qbraid logo" style="width:60px;height:60px;">
      <span> qBraid</span>
      <span style="color:#808080"> | Pyqasm</span>
      <img src="_static/pyqasm_logo.svg" alt="pyqasm logo" style="width:50px;height:50px;">
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

Python toolkit providing an OpenQASM 3 semantic analyzer and utilities for program analysis and compilation. Built on top of the `openqasm <https://github.com/openqasm/openqasm>`_ python package, it extends its capabilities with semantic analysis and program unrolling.
Pyqasm is presently used in the `qBraid-QIR <https://github.com/qBraid/qbraid-qir>`_ project, enabling the conversion of OpenQASM programs to the Quantum Intermediate Representation (QIR).



Installation
-------------

Pyqasm requires Python 3.10 or greater. The base package can be installed with pip as follows:

.. code-block:: bash

   pip install pyqasm


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
   :maxdepth: 1
   :caption: Pyqasm API Reference
   :hidden:

   api/pyqasm
